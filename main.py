from modules.scraper import Scraper
from modules.utils import ask_input, ask_multiple_option
import matplotlib.pyplot as plt
import math
import pandas as pd

def benford_analysis(data):
    print("\n=== ANÁLISIS LEY DE BENFORD ===")

    first_digits = []
    for user, followers in data.items():
        if isinstance(followers, int) and followers > 0:
            first_digits.append(int(str(followers)[0]))

    if not first_digits:
        print("No hay datos válidos para analizar.")
        return

    total = len(first_digits)
    freqs = {d: first_digits.count(d) / total * 100 for d in range(1, 10)}
    benford = {d: math.log10(1 + 1/d) * 100 for d in range(1, 10)}

    print(f"{'Dígito':<8}{'Observado (%)':<15}{'Benford (%)':<12}{'Desviación (%)':<15}")
    desviaciones = []
    for d in range(1, 10):
        desviacion = abs(freqs[d] - benford[d])
        desviaciones.append(desviacion)
        print(f"{d:<8}{freqs[d]:<15.2f}{benford[d]:<12.2f}{desviacion:<15.2f}")

    plt.figure(figsize=(9,5))
    plt.bar(freqs.keys(), freqs.values(), label="Frecuencia observada", alpha=0.7, color='skyblue')

    plt.plot(list(freqs.keys()), list(freqs.values()), 'b-o', linewidth=2, label="Tendencia observada")

    plt.plot(list(benford.keys()), list(benford.values()), 'r--o', linewidth=2, label="Ley de Benford (Real)")

    plt.xlabel("Primer dígito")
    plt.ylabel("Frecuencia (%)")
    plt.title("Comparación con la Ley de Benford")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.show()

    desviacion_promedio = sum(desviaciones) / 9
    print(f"\nDesviación promedio: {desviacion_promedio:.2f}%")

    if desviacion_promedio <= 12:
        print("Conclusión: Cuenta real (desviacion inferior al 12%).")
    else:
        print("Conclusión: Cuenta bot (desviación superior al 12%).")

groups = ['followers', 'following']

target = ask_input('Enter the target username: ')
group = ask_multiple_option(options = groups + ['both']);
print('\nEnter your Instagram credentials')
username = ask_input('Username: ')
password = ask_input(is_password = True)

from modules.scraper import Scraper

def scrape(group_type):
    # Rutas (Mantenemos tus rutas actuales)
    chromedriver_path = r"C:\Users\Luis\Desktop\instagram-followers-scraper-master\instagram-followers-scraper-master\drivers\chromedriver.exe"
    cookies_path = r"C:\Users\Luis\Desktop\instagram-followers-scraper-master\instagram-followers-scraper-master\cookies.json"

    driver = Scraper.create_driver(chromedriver_path)
    
    print(f"--- Iniciando Scraping de {group_type} para: {target} ---")
    session_ok = Scraper.load_simple_cookies_and_auth(driver, cookies_path)

    scraper = Scraper(target)
    scraper.driver = driver

    if not session_ok:
        scraper.authenticate(username, password)

    # 1. Obtener la lista de seguidos
    links = scraper.get_users(group_type, verbose=True)
    print(f"Se obtuvieron {len(links)} usuarios.")
    
    # 2. Obtener datos adicionales (Bio, Seguidores, etc.)
    # Aquí es donde llamaremos a la nueva lógica que extraerá la BIO
    user_data_list = []
    
    # Para la prueba, limitaremos a los primeros 20 para no ser bloqueados, 
    # pero puedes quitar el [:20] si es necesario.
    for user_url in links[:20]: 
        details = scraper.get_user_info(user_url) # Esta función la crearemos en scraper.py
        user_data_list.append(details)

    # 3. Exportar a CSV/Excel (Punto 2 de la prueba)
    df = pd.DataFrame(user_data_list)
    df.to_csv("reporte_seguidos_hemisemetre.csv", index=False, encoding='utf-8-sig')
    print("✅ Archivo 'reporte_seguidos_hemisemetre.csv' generado con éxito.")

    # 4. Análisis de Benford (Punto 3 - Estrategia)
    # Convertimos los datos para que tu función de Benford siga funcionando
    followers_dict = {item['username']: item['followers_count'] for item in user_data_list if 'followers_count' in item}
    
    scraper.close()

    if followers_dict:
        benford_analysis(followers_dict)

if __name__ == "__main__":
    # La prueba pide los SEGUIDOS de @nayelynxx
    target = "nayelynxx" 
    scrape("following")