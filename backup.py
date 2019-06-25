import datetime
import pandas as pd
from openpyxl import load_workbook



def now():
    now = datetime.datetime.now()
    now = str(now.strftime("%d.%m.%Y-%H.%M"))
    return now

def backup(data):    
    with pd.ExcelWriter(now()) as writer:  
        sheetname = now()
        data.to_excel(writer, sheet_name=sheetname)
