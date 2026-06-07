import sys
import os

import certifi
ca = certifi.where()

from dotenv import load_dotenv
load_dotenv()

mongo_db_url = os.getenv("MONGODB_URL_KEY")
print(mongo_db_url)

import pymongo
import pandas as pd

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.responses import RedirectResponse
from uvicorn import run as app_run

from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.pipeline.training_pipeline import TrainingPipeline
from networksecurity.utils.main_utils.utils import load_object
from networksecurity.utils.ml_utils.model.estimator import NetworkModel

client = pymongo.MongoClient(mongo_db_url, tlsCAFile=ca)

from networksecurity.constant.training_pipeline import (
    DATA_INGESTION_COLLECTION_NAME,
    DATA_INGESTION_DATABASE_NAME
)

database = client[DATA_INGESTION_DATABASE_NAME]
collection = database[DATA_INGESTION_COLLECTION_NAME]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["authentication"])
async def index():
    return RedirectResponse(url="/docs")


@app.get("/train")
async def train_route():
    try:
        train_pipeline = TrainingPipeline()
        train_pipeline.run_pipeline()
        return Response("Training is successful")
    except Exception as e:
        raise NetworkSecurityException(e, sys)


@app.post("/predict")
async def predict_route(request: Request, file: UploadFile = File(...)):
    try:
        # Read uploaded csv
        df = pd.read_csv(file.file)

        # Load preprocessor and model
        preprocessor = load_object("final_model/preprocessor.pkl")
        final_model = load_object("final_model/model.pkl")

        network_model = NetworkModel(
            preprocessor=preprocessor,
            model=final_model
        )

        # Predict
        y_pred = network_model.predict(df)

        # Add prediction column
        df["predicted_column"] = y_pred

        # Create output folder if missing
        os.makedirs("prediction_output", exist_ok=True)

        # Save output
        output_path = "prediction_output/output.csv"
        df.to_csv(output_path, index=False)

        # Create HTML table
        table_html = df.head(100).to_html(
            classes="table table-striped",
            index=False
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Prediction Results</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                }}

                table {{
                    border-collapse: collapse;
                    width: 100%;
                }}

                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                }}

                th {{
                    background-color: #f2f2f2;
                }}

                h2 {{
                    color: #333;
                }}
            </style>
        </head>
        <body>

            <h2>Prediction Completed Successfully</h2>

            <p><b>Total Records:</b> {len(df)}</p>

            <p><b>Output Saved At:</b> {output_path}</p>

            <p><b>Showing First 100 Rows</b></p>

            {table_html}

        </body>
        </html>
        """

        return Response(
            content=html_content,
            media_type="text/html"
        )

    except Exception as e:
        print(e)
        raise NetworkSecurityException(e, sys)


if __name__ == "__main__":
    app_run(
        app,
        host="0.0.0.0",
        port=8000
    )