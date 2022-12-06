import requests
import sqlite3
import pandas
import time
import logging
import datetime

logging.basicConfig(level=logging.INFO, filename="logging/detmir_logging_" + time.strftime("%Y_%m_%d-%H_%M") + ".txt", filemode="w",
                    encoding='utf-8',
                    format="%(asctime)s %(levelname)s %(message)s")

connect = sqlite3.connect("Detmir.db")
cursor = connect.cursor()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}

def createtable_products():
    cursor.execute("""CREATE TABLE IF NOT EXISTS products(
        product_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        product_category_lvl1 TEXT,
        product_category_lvl2 TEXT,
        product_category_lvl3 TEXT,
        product_title TEXT,
        product_price DOUBLE,
        product_old_price DOUBLE,
        product_code INTEGER
    )
    """)
    connect.commit()
def insert_products(product_info):
    sql = """   INSERT INTO products (product_category_lvl1, product_category_lvl2, product_category_lvl3, product_title, product_price, product_old_price, product_code) 
                VALUES (?, ?, ?, ?, ?, ?, ?)  """
    cursor.execute(sql, product_info)
    connect.commit()


def response_product(id, title_category_lvl3, title_category_lvl2, title_category_lvl1):
    try:
        response_product = requests.get(
            'https://api.detmir.ru/v2/products?filter=categories[].id:' + id + ';platform:web;priority_stores[].id:%2C1063;promo:false;site:detmir;withregion:RU-BU&expand=meta.facet.ages.adults,meta.facet.gender.adults,webp&meta=*&limit=100&offset=0&sort=forinstore_price:asc',
            headers=headers)
    except requests.exceptions.RequestException as e:
        logging.error("Error connecting to the page")
        logging.error(e)
        raise SystemExit(e)
    total_count = response_product.json()['meta']['length']
    available = True
    logging.info("Parsing products from the category:   " + title_category_lvl2 + "  subcategory:  " + title_category_lvl3)
    for i in range(0, total_count, 100):
        try:
            response_product = requests.get(
                'https://api.detmir.ru/v2/products?filter=categories[].id:' + id + ';platform:web;priority_stores[].id:%2C1063;promo:false;site:detmir;withregion:RU-BU&expand=meta.facet.ages.adults,meta.facet.gender.adults,webp&meta=*&limit=100&offset=' + str(
                    i) + '&sort=forinstore_price:asc',
                headers=headers)
        except requests.exceptions.RequestException as e:
            logging.error("Error connecting to the page")
            logging.error(e)
            raise SystemExit(e)
        items = response_product.json()['items']
        for j in items:
            # Проверка на наличие товара в кэпитал молле
            if ('1063' not in j['available']['offline']['stores']):
                available = False
                break
            old_price = 0
            if (j['old_price'] is None):
                old_price = j['price']['price']
            else:
                old_price = j['old_price']['price']

            # print(j['title'], j['price']['price'], old_price, j['code'])
            product_info = [title_category_lvl1, title_category_lvl2, title_category_lvl3, j['title'],
                            j['price']['price'], old_price, j['code']]
            insert_products(product_info)
        if (available == False):
            break
        time.sleep(1.5)


#Функция для сбора информации по категориям в "Питание и кормление"
def nutrition_feeding():
    title_category_lvl1 = "Питание и кормление"
    logging.info("CATEGORY ПИТАНИЕ И КОРМЛЕНИЕ")
    #nf_logger = logging.getLogger("nutrition_feeding")
    #nf_logger.setLevel(logging.INFO)
    try:
        r = requests.get('https://api.detmir.ru/v2/categories?filter=alias:nutrition_feeding&expand=categories',
                         headers=headers)
    except requests.exceptions.RequestException as e:
        logging.error("Error connecting to categories inside 'NUTRITION AND FEEDING'")
        logging.error(e)
        raise SystemExit(e)

    categories = (r.json()['data'][0]['categories'])
    #print(r.json()['data'][0]['title'] + ":")
    #Подкатегории (2 уровень) В "Питание и кормление"
    for i in categories:
        #print(i['title'] + ": ")
        #Подкатегории (3 уровень)
        for j in i['categories']:
            #print("    " + j['title'] + " " + j['id'])
            response_product(j['id'], j['title'], i['title'], title_category_lvl1)

#Функция для сбора информации по категориям в "Гигиена и уход"
def hygiene_care():
    title_category_lvl1 = "Гигиена и уход"
    logging.info("CATEGORY ГИГИЕНА И УХОД")
    #hc_logger = logging.getLogger("hygiene_care")
    #hc_logger.setLevel(logging.INFO)
    try:
        r = requests.get('https://api.detmir.ru/v2/categories?filter=alias:hygiene_care&expand=categories',
                         headers=headers)
    except requests.exceptions.RequestException as e:
        logging.error("Error when connecting to categories inside 'HYGIENE AND CARE'")
        logging.error(e)
        raise SystemExit(e)

    categories = (r.json()['data'][0]['categories'])
    #print(r.json()['data'][0]['title'] + ":")
    #Подкатегории (2 уровень) В "Гигиена и уход"
    for i in categories:
        #print(i['title'] + ": ")
        #Подкатегории (3 уровень)
        for j in i['categories']:
            #print("    " + j['title'] + " " + j['id'])
            response_product(j['id'], j['title'], i['title'], title_category_lvl1)

#Функция для сбора информации по продуктам в подкатегориях

def import_to_excel():
    logging.info("Writing from the database to Excel")
    df = pandas.read_sql(
        "select product_category_lvl1 as 'Основная категория', product_category_lvl2 as 'Подкатегория', product_category_lvl3 as 'Подкатегория', product_title as 'Наименование', product_price as 'Цена по акции', product_old_price as 'Цена', product_code as 'Код товара' from products ", connect)
    df.to_excel(r"Excel\detmir_" + time.strftime("%Y_%m_%d") + ".xlsx", index=False)
    sql_delete_query = """ DELETE FROM products"""
    cursor.execute(sql_delete_query)
    connect.commit()
    logging.info("The database table has been cleared")
    #print ("Таблица в базе данных успешно очищена")

#createtable_products()

start = datetime.datetime.now()
logging.info("The parser is running")
nutrition_feeding()
hygiene_care()
import_to_excel()
logging.info("The parser has finished working")
end = datetime.datetime.now()
logging.info("Program execution time: " + str(end-start))