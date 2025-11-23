# Standard library imports
import os
import re
import time
import warnings
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

# Third-party imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import openpyxl
import xlsxwriter
import pymysql
from sqlalchemy import create_engine
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
# import functions
from utils import get_commcare_odata
# Download charges virales database from "Charges_virales_pediatriques.sql file"
from caris_fonctions import execute_sql_query

# In[2]:
from utils import get_commcare_odata
from ptme_fonction import creer_colonne_match_conditional



# Download charges virales database from "Charges_virales_pediatriques.sql file"
from caris_fonctions import execute_sql_query
env_path = 'dot.env'
sql_file_path = './specimen.sql'

ptme_enceinte = execute_sql_query(env_path, sql_file_path)
duplicates = ptme_enceinte.columns[ptme_enceinte.columns.duplicated()].tolist()
if duplicates:
    print("Attention : des colonnes en double ont été trouvées dans le DataFrame.")
    print("Colonnes en double :", duplicates)
else:
    print("Aucune colonne en double trouvée dans le DataFrame.")
# print the shape of the DataFrame
print(ptme_enceinte.shape[0])
# print the first few rows of the DataFrame
print(ptme_enceinte.head(2))

ptme_enceinte.to_excel('specimen.xlsx', index=False)