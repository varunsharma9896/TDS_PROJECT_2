from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import zipfile
import os
import io
import logging
from groq import Groq
import dotenv
import pandas as pd

# Load environment variables
dotenv.load_dotenv()

# Initialize FastAPI app
app = FastAPI()

@app.get("/")
async def root():
    """Root endpoint to verify the server is running."""
    return {"message": "Hello, World!"}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY is missing. Please set it in the .env file.")

client = Groq(api_key=GROQ_API_KEY)  # Use environment variable directly


@app.post("/api/")
async def process_request(file: UploadFile = File(...)):
    """
    API to process uploaded ZIP file containing a CSV file.
    The CSV should contain a column named 'question', which will be passed to the LLM.
    """
    print(f"Received file: {file.filename}")

    # Validate API Key
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API Key. Check .env file.")

    try:
        # Check if the uploaded file is a ZIP file
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a ZIP file.")
        
        # Read the contents of the uploaded ZIP file
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)

        # Extract ZIP file and validate its contents
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            file_names = zip_ref.namelist()

            # Ensure only one CSV file is inside the ZIP
            csv_files = [f for f in file_names if f.endswith(".csv")]
            if len(csv_files) != 1:
                raise HTTPException(status_code=400, detail="ZIP must contain exactly one CSV file.")
            
            # Extract the CSV file to a temporary directory
            extracted_dir = "extracted_files"
            os.makedirs(extracted_dir, exist_ok=True)
            zip_ref.extract(csv_files[0], path=extracted_dir)

            csv_file_path = os.path.join(extracted_dir, csv_files[0])
            
            # Read the CSV file into a DataFrame
            df = pd.read_csv(csv_file_path)
            logger.info("CSV file read successfully.")

        print("CSV file read successfully.")
        print(df.head())  # Display the first few rows of the DataFrame
        
        if "question" not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain a 'question' column.")

        answers = {}

        for question in df['question']:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": question}],
                model="llama3-8b-8192",
            )
            answers[question] = chat_completion.choices[0].message.content

        # Clean up: Delete the extracted CSV file after processing
        os.remove(csv_file_path)
        print("CSV file processed and deleted successfully.")
        
        return {"responses": answers}

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": str(e)}
