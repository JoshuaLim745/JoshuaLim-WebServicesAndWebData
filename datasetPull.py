# Taken from Kaggle code button
# It is on the same page as the dataset
# https://www.kaggle.com/datasets/bilalyussef/google-books-dataset

# Install dependencies as needed:
# pip install kagglehub[pandas-datasets]
# kaggle api token = KGAT_9fa7ea5aad925679173bb4e81193551c
# export KAGGLE_API_TOKEN=KGAT_9fa7ea5aad925679173bb4e81193551c
# kaggle competitions list




#Might continue might not



import kagglehub
from kagglehub import KaggleDatasetAdapter

kagglehub.login()
# Set the path to the file you'd like to load
file_path = "google_books_1299.csv"

df = kagglehub.load_dataset(
    KaggleDatasetAdapter.PANDAS,
    "bilalyussef/google-books-dataset",
    file_path,
    pandas_kwargs={"encoding": "ISO-8859-1"}
)

"""     pandas_kwargs={
    "encoding": "ISO-8859-1", 
    # Use the exact names found in the CSV header
    "usecols": ["title", "authors", "average_rating", "categories", "description"]
} """

df.columns = ["title", "author", "avg rating", "list of genre", "description"]

print("First 5 records:", df.head())
