"""
Holds all the important logic
"""
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()



"""
TODO: Functions / endpoints needed in main
1. Import book data to DB
    Kaggle/Goodreads/Google Books  for data
    Using (sqlite/sqlalchemy) - for database querying
2. CRUD for User data
    Create user data - From the swagger UI Doc we can just execute some lines.  
    Read - Return user data - possibly like a user profile to just show logged in user data
    Update - similar to above we just allow users to edit their profile. 
    Delete user data - Just a true or false ig
3. Login page with security such as tokens
4. Personalised suggestions. - recommend stuff based on user preferences - link to userID
    Content-Based Filtering.
    Look at the user's top-rated books (e.g., books they gave 5 stars).
    Identify the most common genre among those top books.
    Suggest 3 books from the Google Books API that match that genre but are not currently in the user's local database.
5. Genre Trends - Just query table and tally genres and order by popularity - can be for books or users - Some sort of true or false can be used to determine which table to take from. 

"""


class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_price": item.price, "item_id": item_id}