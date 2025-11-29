import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import PyPDF2
import io
import base64

class DataProcessor:
    @staticmethod
    def process_csv(filepath):
        return pd.read_csv(filepath)
    
    @staticmethod
    def process_excel(filepath):
        return pd.read_excel(filepath)
    
    @staticmethod
    def process_pdf(filepath):
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    
    @staticmethod
    def create_chart(data, chart_type="bar"):
        if chart_type == "bar":
            fig = px.bar(data)
        elif chart_type == "line":
            fig = px.line(data)
        elif chart_type == "scatter":
            fig = px.scatter(data)
        
        img_bytes = fig.to_image(format="png")
        return base64.b64encode(img_bytes).decode()
    
    @staticmethod
    def analyze_data(df, operation="describe"):
        if operation == "describe":
            return df.describe().to_dict()
        elif operation == "mean":
            return df.mean().to_dict()
        elif operation == "sum":
            return df.sum().to_dict()