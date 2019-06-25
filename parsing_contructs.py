# Функция расчитана на парсинг нужной информации с сайта гос.закупок.
import requests
from bs4 import BeautifulSoup as BS
import bs4
import time
from fake_useragent import UserAgent
import re 
#from decimal import Decimal
import numpy as np
import pandas as pd
import shutil
import os
from backup import backup
from backup import now


link_main_pattern = 'http://zakupki.gov.ru'
# link_pattern_fz44_order_info = 'http://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber='
link_pattern_fz44_result_info = 'http://zakupki.gov.ru/epz/order/notice/ea44/view/supplier-results.html?regNumber='
# link_pattern_fz44_documents = 'http://zakupki.gov.ru/epz/order/notice/ea44/view/documents.html?regNumber='
# link_pattern_fz44_contract_info = 'http://zakupki.gov.ru/epz/contract/extendedsearch/results.html?searchString=&orderNumber='
link_pattern_fz44_contruct = 'http://zakupki.gov.ru/epz/contract/contractCard/document-info.html?reestrNumber='
link_pattern_fz223 = 'http://zakupki.gov.ru/223/purchase/public/purchase/info/common-info.html?regNumber='
link_fz223_documents = 'http://zakupki.gov.ru/223/purchase/public/purchase/info/documents.html?regNumber='

### Перечень локальных функций:

# функция загружает страницу в суп
def get_page(link):
    page = requests.get(link, headers={'User-Agent': UserAgent().chrome})
    page.encoding = 'utf8'
    page = page.text
    soup = BS(page)
    while soup.title.text == ' Страница не найдена ':
        time.sleep(5)
        get_page(link)
    return soup

# Функция очищает атрибут тега текст от артефактов, переносов и пр.
def clear_text(content):
    content = re.sub(r'[\n]+', '', content) # Очистили от переносов
    content = re.sub(r'[\s]{2,}', '', content) # Очистили от лишних пробелов
    content = re.sub(r'\xa0', '', content) # Соединили цену
    content = re.sub(r',', '.', content) # изменили запись для возможности преобрадования str в decimal
    content = re.sub(r' Российский рубль', '', content) # убираем валюту
    return content


# Пробегает страницу в поисках информации о победителе
def get_win_info_44(order_num):
    link = link_pattern_fz44_result_info + order_num
    soup = get_page(link)
    winner = soup.find_all('td')[-3].text # опытным путём определил, где находится наименование победителя
    winner = clear_text(winner)
    
    winner_price = soup.find_all('td')[-2].text
    winner_price = clear_text(winner_price)
    if winner_price != '':
        winner_price = float(winner_price)

        contruct_link_div = soup.find_all('a', href=True)[-1]
        link_to_contruct_info = link_main_pattern + contruct_link_div.get('href') # парсим ссылку на страницу
        num_of_contruct = str(contruct_link_div.text.replace('№','')) #  парсим номер контракта и освобождаем его от значка №


        df = pd.DataFrame({
        'Реестровый номер закупки': [order_num],
        'победитель': [winner],
        'цена контракта после снижения': [winner_price],
        'номер контракта': [num_of_contruct]
        })
    
        return df
    
# Вспомогательная функция для тестов
def get_empty_dataframe():
    df = pd.DataFrame({
    'Реестровый номер закупки': [],
    'победитель': [],
    'цена контракта после снижения': [],
    'номер контракта': []
    })
    
    return df

# скачивает контракт по фз-44
def get_contruct44(contruct_num):
    link = link_pattern_fz44_contruct + contruct_num
    soup = get_page(link)
    contruct_div = soup.find_all('a', class_='')[2] 
    file_name = contruct_div.get('title')
    link_to_contruct = contruct_div.get('href')
    directory = 'contructs/'
    
    
    file = requests.get(link_to_contruct, stream=True, headers={'User-Agent': UserAgent().chrome})
    
    if file.headers.get('Content-Disposition') is not None:
        file_extension = re.findall(r'\.[a-z]+', file_name)[0]
    else:
        file_extension = ''
        
    filename =  directory + contruct_num + file_extension
    
    if not os.path.isdir(directory):
        os.mkdir(directory) 
    
    if file.status_code == 200:
        with open(filename, 'wb') as f:
            file.raw.decode_content = True
            shutil.copyfileobj(file.raw, f)

# скачивает  все документы закупки по фз-233 в папку ~/номер закупки           
def get_contruct233(order_num):
    link = link_fz223_documents + order_num
    soup = get_page(link)
    documents_div = soup.find_all('a', class_='epz_aware')
    directory = 'C:/Users/v.mazeiko/Documents/Парсинг Госзаупок/contructs/' + order_num

    if not os.path.isdir(directory):
        os.mkdir(directory) 

    for i in range(0, len(documents_div)-1):
        link_to_file = link_main_pattern + documents_div[i].get('href') 
    
        file = requests.get(link, stream=True, headers={'User-Agent': UserAgent().chrome})
        file.encoding = 'utf-8'
    
        if file.headers.get('Content-Disposition') is not None:
            file_extension = re.findall(r'\.[a-z][^\n]+', file.headers.get('Content-Disposition'))
        else:
            file_extension = ''
        file_name = clear_text(documents_div[i].text) + file_extension
        save_here = directory + '//' + file_name
        if file.status_code == 200:
            with open(save_here, 'wb') as f:
                file.raw.decode_content = True
                shutil.copyfileobj(file.raw, f)             

# Информация о победителях по фз223                
def get_win_info_233(order_num, pause):
    link_fz223_contructs_links = 'http://zakupki.gov.ru/223/purchase/public/purchase/info/contractInfo.html?regNumber='
    link = link_fz223_contructs_links + str(order_num)
    
    soup = get_page(link)
    
    link = soup.find_all('li')[0].get('onclick')
    if link is None:
        df = get_empty_dataframe()
        df['Реестровый номер закупки'] = order_num
        return df
    
    link = re.sub(r'window\.open\(\'|\'\)', '', link)
    link = re.sub(r'view-common', r'view-subject', link)
    link = link_main_pattern + link
    soup = get_page(link)
    time.sleep(pause)

    winner = soup.find_all('td')[-7].text
    winner_price = soup.find_all('td')[10].text

    if winner_price != '':
            winner_price =  winner_price #winner_price = float(winner_price)
    
            contruct_link_div = soup.find_all('a', href=True)[-1]
            link_to_contruct_info = link_main_pattern + contruct_link_div.get('href') # парсим ссылку на страницу
            num_of_contruct = re.findall(r'[\d-]+', clear_text(soup.h1.string))[0] #  парсим номер контракта
    
    
            df = pd.DataFrame({
            'Реестровый номер закупки': [order_num],
            'победитель': [winner],
            'цена контракта после снижения': [winner_price],
            'номер контракта': [num_of_contruct]
            })
            
            return df            
  