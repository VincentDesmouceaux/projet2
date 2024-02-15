import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib
import time
import os
import ssl

base_url = "https://books.toscrape.com/index.html"
data_folder = 'data'
if not os.path.exists(data_folder):
    os.makedirs(data_folder)


# Fonction pour extraire les liens des catégories depuis la page d'accueil
def extract_category_links(url):
    links = []
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        category_div = soup.find('div', class_='side_categories')
        if category_div:
            links = [urljoin(url, a['href']) for a in category_div.find_all('a')]
        return links
    return links


# Fonction pour extraire les liens des pages de produits et le lien vers la page suivante
def extract_product_links(url):
    links = []
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        product_divs = soup.find_all('h3')
        links = [urljoin(url, div.a['href']) for div in product_divs]
        next_page = soup.find('li', class_='next')
        next_page_link = urljoin(url, next_page.a['href']) if next_page and next_page.a else None
        return links, next_page_link
    return links, None


def download_image(image_url, destination_folder, category, title):
    try:
        context = ssl._create_unverified_context()
        response = urllib.request.urlopen(image_url, context=context)
        image_data = response.read()
        image_name = f"{title}.jpg"
        destination_path = os.path.join(destination_folder, image_name)

        with open(destination_path, 'wb') as image_file:
            image_file.write(image_data)
        print(f"Image downloaded: {image_name}")
        return destination_path
    except Exception as e:
        print(f"Error downloading image: {image_url}. {str(e)}")
        return None


# Fonction pour extraire les informations produit pour chaque lien de livre
def extract_product_info(product_url, category_folder, category):
    response = requests.get(product_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        # Extraction des informations souhaitées
        product_page_url = product_url
        upc = soup.find('th', string='UPC').find_next('td').text.strip() if soup.find('th', string='UPC') else None
        title = soup.find('h1').text.strip()
        price_including_tax = soup.find('th', string='Price (incl. tax)').find_next('td').text.strip()
        price_excluding_tax = soup.find('th', string='Price (excl. tax)').find_next('td').text.strip()
        number_available = soup.find('th', string='Availability').find_next('td').text.strip()
        product_description = soup.find('meta', attrs={'name': 'description'})['content'].strip()
        review_rating = soup.find('p', class_='star-rating')['class'][1].strip()
        image_url = urljoin(base_url, soup.find('div', class_='item active').img['src'].replace('../../', ''))
        image_path = download_image(image_url, category_folder, category, title)

        return {
            'product_page_url': product_page_url,
            'upc': upc,
            'title': title,
            'price_including_tax': price_including_tax,
            'price_excluding_tax': price_excluding_tax,
            'number_available': number_available,
            'product_description': product_description,
            'review_rating': review_rating,
            'image_url': image_url,
            'image_path': image_path
        }


# Extraction des informations pour toutes les catégories depuis la page d'accueil
all_category_links = extract_category_links(base_url)

for category_link in all_category_links:
    print(f"Processing category: {category_link}")

    # Créer un dossier pour chaque catégorie
    category_name = category_link.split('/')[-2]
    category_folder = os.path.join(data_folder, category_name)
    if not os.path.exists(category_folder):
        os.makedirs(category_folder)

    all_product_links = []
    page_url = category_link
    while page_url:
        links_on_page, next_page_link = extract_product_links(page_url)
        if not links_on_page:
            break
        all_product_links.extend(links_on_page)
        page_url = next_page_link
       

    if not all_product_links:
        print("No product links found for this category.")
        continue

    all_product_info = []
    for product_link in all_product_links:
        print(f"Processing product link: {product_link}")
        product_info = extract_product_info(product_link, category_folder, category_name)

        if not product_info:
            print(f"Error processing product link: {product_link}")
            continue
        all_product_info.append(product_info)
       

    if not all_product_info:
        print(f"No product info found for this category: {category_link}")
        continue

    csv_file = f'{category_name}_books.csv'
    csv_path = os.path.join(category_folder, csv_file)
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = all_product_info[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for product_info in all_product_info:
            writer.writerow(product_info)
        print(f"{category_name} books saved to {csv_path}")
   
