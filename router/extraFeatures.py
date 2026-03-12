from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from databaseModel import Book, Genre, User, UserRatesBook, book_genre_link, user_genre_link, get_db
from passlib.context import CryptContext
import bcrypt
from google import genai
from auth import get_current_user
import os
from dotenv import load_dotenv


class BookSuggestionResponse(BaseModel):
    id: int
    title: str
    author: str
    avgRating: float = Field(..., alias="avg_Rating")
    genres: List[str]

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # 1. Encode string to bytes
    # 2. Truncate to 72 bytes (bcrypt limit)
    pwd_bytes = password.encode('utf-8')[:72]
    
    # 3. Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    
    # 4. Return as a string so it can be stored in PostgreSQL
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # 1. Prepare inputs (truncate plain text to match)
        pwd_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        
        # 2. Check compatibility
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

router = APIRouter(prefix="/Extra-Features")











@router.get("/trends/{target}", summary="Get Genre Trends", operation_id="getGenreTrends", tags=["Analysis & AI Tools"])
def get_trends(target: str, db: Session = Depends(get_db)):

    """
    ### Genre Trend Analysis
    Aggregates data to show which genres are currently the most popular.
    
    * **Input**:
        * 'Target': Has 2 values. Book or User 
            * `Book`: Tallies and lists the most popular genre of books in the database.
            * `User`: Tallies and lists the most popular genre among users.
    * **Logic**: Uses PostgreSQL `COUNT` and `GROUP BY` functions for efficient tallying.
    * **Output**: A dictionary of genres ordered from most to least popular.
    """

    target_type = target.lower()
    
    if target_type == "book":
        # Popularity by number of books in a genre
        book_count_func = func.count(book_genre_link.c.book_id)
        results = (
            db.query(Genre.name, book_count_func.label("total"))
            .join(book_genre_link)
            .group_by(Genre.name)
            .order_by(desc(book_count_func)) # Correct: desc() on the function object
            .all()
        )
    elif target_type == "user":
        # Popularity by number of users who favorited a genre
        user_count_func = func.count(user_genre_link.c.user_id)
        results = (
            db.query(Genre.name, user_count_func.label("total"))
            .join(user_genre_link)
            .group_by(Genre.name)
            .order_by(desc(user_count_func)) # Correct: desc() on the function object
            .all()
        )
    else:
        raise HTTPException(
            status_code=400, 
            detail="Invalid target. Please use 'book' or 'user'."
        )
    
    # Returns a dictionary like {"Fantasy": 10, "Sci-Fi": 8}
    return {name: count for name, count in results}











@router.post("/suggestions", summary="Get book recommendations", response_model=List[BookSuggestionResponse], operation_id="getBookSuggestions", tags=["Analysis & AI Tools"])
def get_suggestions(
    db: Session = Depends(get_db), 
    token: Optional[str] = None,
    current_user: User = Depends(lambda token=None: get_current_user(ai_token=token))
):
    """
    ### Personalized Recommendations Engine
    Generates a curated list of books based on a user's specific reading tastes.

    * **Input**:
        * `Token`: Used to identify the user making the request (Optional and can be left blank. As this is for Claude Desktop).
        * `Email`: User email
        * `Password`: User password
    * **Output**: A list of up to 3 with their bookID, title, author, and all their respective genre.
    * **Empty State**: Returns an empty list `[]` if the user's top genre is fully explored.
    * **Error State**: Returns a `404` if the user has no rating history.
    """
    # 1. Get genre IDs from current_user's favorites
    fav_genre_ids = [g.id for g in current_user.fav_genres]

    # 2. Get genre IDs from current_user's high ratings (4+ stars)
    rated_genre_ids = db.scalars(
        select(book_genre_link.c.genre_id)
        .join(UserRatesBook, UserRatesBook.book_id == book_genre_link.c.book_id)
        .filter(UserRatesBook.user_id == current_user.id, UserRatesBook.user_rating >= 4.0)
    ).all()

    all_target_genre_ids = list(set(fav_genre_ids) | set(rated_genre_ids))

    if not all_target_genre_ids:
        raise HTTPException(status_code=404, detail="No favorites or high ratings found to generate suggestions.")

    # 3. Find books that have ANY of these genres and haven't been rated yet
    rated_books = select(UserRatesBook.book_id).where(UserRatesBook.user_id == current_user.id)
    
    subquery = (
        select(Book)
        .join(book_genre_link)
        .filter(
            book_genre_link.c.genre_id.in_(all_target_genre_ids),
            ~Book.id.in_(rated_books)
        )
        .distinct()
        .subquery()
    )

    # This outer query takes that unique set and randomizes it
    # We alias the subquery back to the Book model so SQLAlchemy knows how to load it
    suggestions_query = (
        select(Book)
        .select_from(subquery)
        .order_by(func.random())
        .limit(3)
    )

    suggestions = db.scalars(suggestions_query).all()

    # 4. Map to Response
    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "avgRating": b.avg_rating,
            "genres": [g.name for g in b.genres]
        } for b in suggestions
    ]














# AI generated description

def generate_ai_description(book_title: str, author: str) -> str:
    """Helper function to call Gemini 3 Flash."""
    load_dotenv()
    api_key = os.getenv("API_KEY")
    client = genai.Client(api_key=api_key)
    if not api_key:
        raise HTTPException(status_code=400, detail="No API_KEY found in environment variables!")
    
    try:

        prompt = f"Write a compelling, concise 3-sentence book description for '{book_title}' by {author}."
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API Error: {str(e)}")



@router.get("/ai-description", summary="Generate AI description", operation_id="generateBookDescriptionAI", tags=["Analysis & AI Tools"])
def get_book_description_ai(book_id: int, db: Session = Depends(get_db)):
    """
    ### AI Book Description Generator
    Uses the **Gemini 3 Flash** model to generate a custom description based on the book's title.

    * **Step 1**: Looks up the `book_id` in the database to retrieve the `title` and `author`.
    * **Step 2**: Passes that data to the Gemini API.
    * **Step 3**: Returns the natively generated text.
    """
    # 1. Find the book in the database
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found in database")

    # 2. Generate the description using Gemini
    ai_text = generate_ai_description(book.title, book.author)

    # 3. Return the response in camelCase
    return {
        "bookId": book.id,
        "bookTitle": book.title,
        "aiGeneratedDescription": ai_text
    }










