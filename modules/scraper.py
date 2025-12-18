import re
import time
import json
import os
import random

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException


class Scraper(object):
    """Able to start up a browser, to authenticate to Instagram and get
    followers and people following a specific user."""

    @staticmethod
    def create_driver(chromedriver_path):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            },
        )
        return driver

    @staticmethod
    def load_simple_cookies_and_auth(driver, cookies_simple_json_path="cookies.json"):
        if not os.path.exists(cookies_simple_json_path):
            return False

        # ESTO EVITA LA PANTALLA BLANCA: Ir a una página real antes de las cookies
        driver.get("https://www.instagram.com/accounts/login/") 
        time.sleep(3) 

        # Espera a que el anuncio aparezca
        time.sleep(4) 
        try:
            # Intenta cerrar el modal de "Mensajes" o "Notificaciones"
            pop_up = driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar') or contains(text(), 'Ahora no')]")
            pop_up.click()
            print("Pop-up cerrado con éxito.")
        except:
            print("No se detectó pop-up o se cerró manualmente.")
        
        return True

    def __init__(self, target, chromedriver_path=None, cookies_path="cookies.json"):
        self.target = target

        self.driver = self.create_driver(chromedriver_path)

        cookies_loaded = False
        try:
            cookies_loaded = self.load_simple_cookies_and_auth(
                self.driver, cookies_path
            )
        except Exception as e:
            cookies_loaded = False

        self._cookies_loaded = cookies_loaded

    def close(self):
        """Close the browser."""

        self.driver.close()

    def authenticate(self, username, password):
        """Log in to Instagram with the provided credentials."""

        print("\nLogging in…")
        self.driver.get("https://www.instagram.com")

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )

        username_input = self.driver.find_element(By.NAME, "username")
        password_input = self.driver.find_element(By.NAME, "password")

        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        time.sleep(1)

    def get_users(self, group, verbose=False, max_scrolls=500, max_inactivity=25):
        """
        Obtiene todos los seguidores o seguidos haciendo scroll automático (versión más estable).
        """
        import time
        from selenium.webdriver.common.by import By

        link = self._get_link(group)
        self._open_dialog(link)

        print("Scrolleando seguidores...")

        users = set()
        scroll_box = self.users_list_container

        last_height = 0
        same_height_count = 0
        scroll_count = 0
        last_capture_time = time.time()
        retries = 0

        while True:
            scroll_count += 1

            self.driver.execute_script("""
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return;
                const divs = dialog.querySelectorAll('div');
                for (let div of divs) {
                    if (div.scrollHeight > div.clientHeight * 1.2) {
                        div.scrollTop = div.scrollHeight;
                        break;
                    }
                }
            """)

            time.sleep(2)
            links = scroll_box.find_elements(By.XPATH, ".//a[contains(@href, '/')]")
            new_users = 0

            for link in links:
                username = link.text.strip()
                if username and username not in users:
                    users.add(username)
                    new_users += 1
                    if verbose:
                        print(f" {username}")

            if new_users > 0:
                last_capture_time = time.time()
                retries = 0 
            else:
                retries += 1

            print(f"Total: {len(users)}")

            inactivity_time = time.time() - last_capture_time
            if inactivity_time > max_inactivity:
                if retries < 3:
                    print(f"No hay nuevos usuarios, reintentando scroll ({retries}/3)...")
                    time.sleep(3)
                    continue
                else:
                    print("No se detectan nuevas peticiones, scroll detenido definitivamente.")
                    break

            current_height = self.driver.execute_script("""
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return 0;
                const divs = dialog.querySelectorAll('div');
                for (let div of divs) {
                    if (div.scrollHeight > div.clientHeight * 1.2) return div.scrollHeight;
                }
                return 0;
            """)

            if current_height == last_height:
                same_height_count += 1
            else:
                same_height_count = 0
                last_height = current_height

            if same_height_count >= 5:
                print("Scroll parece detenido visualmente, intentando reactivar...")
                time.sleep(3)
                same_height_count = 0

            if scroll_count > max_scrolls:
                print("Límite máximo de scroll alcanzado.")
                break
            
        return list(users)

    def _get_link(self, group):
        self.driver.get(f"https://www.instagram.com/{self.target}/")
        # Espera explícita a que el perfil cargue
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//header"))
        )
        time.sleep(3) # Tiempo extra para renderizado

        # Selector más agresivo para 2025
        xpath_seguidos = f"//a[contains(@href, '/{group}') or contains(@href, '/seguidos')]"
        try:
            target_el = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath_seguidos))
            )
            return target_el
        except:
            print(f"Error: No se encontró el botón de {group}. Reintentando con selector genérico...")
            return self.driver.find_element(By.PARTIAL_LINK_TEXT, "seguidos")

    def _open_dialog(self, link):
        if link is None:
            raise Exception("No se pudo abrir el diálogo: enlace no encontrado.")

        link.click()

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )
        except:
            raise Exception(
                "No se detectó ningún diálogo emergente después de hacer clic."
            )

        try:
            self.users_list_container = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@role='dialog']//div[contains(@class,'_aano')]")
                )
            )
        except:
            try:
                self.users_list_container = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@role='dialog']//div[@class]")
                    )
                )
            except:
                raise Exception(
                    "No se encontró el contenedor de la lista de usuarios en el diálogo."
                )

    def get_followers_count(self, usernames, delay_range=(2, 4)):
        results = {}
        number_re = re.compile(r"([\d,.]+)")

        for i, username in enumerate(usernames, 1):
            url = f"https://www.instagram.com/{username}/"
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//header"))
                )
            except Exception as e:
                print(f"{username}: header no cargó: {e}")
                results[username] = "N/A"
                time.sleep(random.uniform(*delay_range))
                continue

            followers_count = None

            try:
                follower_link = self.driver.find_element(
                    By.XPATH, "//a[contains(@href,'/followers')]"
                )
                raw = (
                    follower_link.get_attribute("title")
                    or follower_link.get_attribute("aria-label")
                    or follower_link.text
                )
                if raw:
                    m = number_re.search(raw)
                    if m:
                        followers_count = m.group(1).replace(",", "").replace(".", "")
            except NoSuchElementException:
                pass
            except Exception:
                pass

            if not followers_count:
                try:
                    meta = self.driver.find_element(
                        By.XPATH, "//meta[@name='description']"
                    )
                    content = meta.get_attribute("content") or ""
                    m = number_re.search(content)
                    if m:
                        followers_count = m.group(1).replace(",", "").replace(".", "")
                except Exception:
                    pass

            if not followers_count:
                try:
                    raw_json = self.driver.execute_script(
                        "return (window._sharedData || window.__initialData || null);"
                    )
                    if raw_json:
                        js_str = str(raw_json)
                        idx = js_str.lower().find("followers")
                        if idx != -1:
                            snippet = js_str[max(0, idx - 120) : idx + 120]
                            m = number_re.search(snippet)
                            if m:
                                followers_count = (
                                    m.group(1).replace(",", "").replace(".", "")
                                )
                    if not followers_count:
                        try:
                            ld = self.driver.find_element(
                                By.XPATH, "//script[@type='application/ld+json']"
                            )
                            ld_text = ld.get_attribute("innerText") or ""
                            m = number_re.search(ld_text)
                            if m:
                                followers_count = (
                                    m.group(1).replace(",", "").replace(".", "")
                                )
                        except Exception:
                            pass
                except Exception:
                    pass

            if not followers_count:
                try:
                    time.sleep(1)
                    follower_link = self.driver.find_element(
                        By.XPATH, "//a[contains(@href,'/followers')]"
                    )
                    raw = (
                        follower_link.get_attribute("title")
                        or follower_link.get_attribute("aria-label")
                        or follower_link.text
                    )
                    if raw:
                        m = number_re.search(raw)
                        if m:
                            followers_count = (
                                m.group(1).replace(",", "").replace(".", "")
                            )
                except Exception:
                    pass

            results[username] = followers_count or "N/A"

            time.sleep(random.uniform(1.5, 2.5))

        return results
    
    def get_user_info(self, username):
        """Extrae nombre completo, seguidores y BIOGRAFÍA de un usuario."""
        url = f"https://www.instagram.com/{username}/"
        data = {
            "username": username,
            "full_name": "N/A",
            "followers_count": 0,
            "biography": "N/A"
        }
        
        try:
            self.driver.get(url)
            # Esperar a que cargue el header del perfil
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//header"))
            )
            time.sleep(random.uniform(2, 4)) # Pausa humana

            # 1. Extraer Nombre Completo
            try:
                # El nombre suele estar en un span dentro del header
                full_name_el = self.driver.find_element(By.XPATH, "//header//section//div[contains(@class, '')]//span")
                data["full_name"] = full_name_el.text
            except: pass

            # 2. Extraer Biografía (Descripción) - PUNTO CLAVE DE LA PRUEBA
            try:
                # La bio suele estar en un contenedor span después del nombre
                bio_el = self.driver.find_element(By.XPATH, "//header//section//div[h1 or h2]/following-sibling::div//span")
                data["biography"] = bio_el.text.replace('\n', ' ') 
            except:
                try:
                    # Selector alternativo para biografías
                    bio_el = self.driver.find_element(By.XPATH, "//main//header//section//div[contains(@class, 'ap1a')]")
                    data["biography"] = bio_el.text.replace('\n', ' ')
                except: pass

            # 3. Extraer Seguidores (reutilizando tu lógica de conteo)
            counts = self.get_followers_count([username])
            data["followers_count"] = counts.get(username, 0)

        except Exception as e:
            print(f"Error extrayendo datos de {username}: {e}")
            
        return data