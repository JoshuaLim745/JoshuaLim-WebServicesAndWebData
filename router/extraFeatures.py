from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from databaseModel import Book, Genre, User, UserRatesBook, book_genre_link, user_genre_link, get_db
from passlib.context import CryptContext
import bcrypt

class UserAuth(BaseModel):
    email: EmailStr
    password: str

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

router = APIRouter(prefix="/Extra Features", tags=["Extra Features"])











@router.get("/trends/{target}", tags=["Analysis"], summary="Get Genre Popularity")
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
        results = (
            db.query(Genre.name, func.count(book_genre_link.c.book_id).label("total"))
            .join(book_genre_link)
            .group_by(Genre.name)
            .order_by(func.desc("total"))
            .all()
        )
    elif target_type == "user":
        # Popularity by number of users who favorited a genre
        results = (
            db.query(Genre.name, func.count(user_genre_link.c.user_id).label("total"))
            .join(user_genre_link)
            .group_by(Genre.name)
            .order_by(func.desc("total"))
            .all()
        )
    else:
        raise HTTPException(
            status_code=400, 
            detail="Invalid target. Please use 'book' or 'user'."
        )
    
    # Returns a dictionary like {"Fantasy": 10, "Sci-Fi": 8}
    return {name: count for name, count in results}












@router.post("/suggestions", tags=["Discovery"], response_model=List[BookSuggestionResponse], summary="Get book recommendations")
def get_suggestions(user_in: UserAuth, db: Session = Depends(get_db)):
    """
    ### Personalized Recommendations Engine
    Generates a curated list of books based on a user's specific reading tastes.

    * **Input**:
        * `Email`: User email
        * `Password`: User password
    * **Output**: A list of up to 3 with their bookID, title, author, and all their respective genre.
    * **Empty State**: Returns an empty list `[]` if the user's top genre is fully explored.
    * **Error State**: Returns a `404` if the user has no rating history.
    """
    # 1. Authenticate
    user = db.query(User).filter_by(email=user_in.email).first()
    if not user or not verify_password(user_in.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    # 2. Collect Genre IDs from two sources:
    
    # Source A: Explicitly favorited genres
    fav_genres_stmt = select(user_genre_link.c.genre_id).where(user_genre_link.c.user_id == user.id)
    fav_genre_ids = db.scalars(fav_genres_stmt).all()

    # Source B: Highly rated genres (User gave 4+ stars)
    rated_genres_stmt = (
        select(book_genre_link.c.genre_id)
        .join(UserRatesBook, UserRatesBook.book_id == book_genre_link.c.book_id)
        .filter(UserRatesBook.user_id == user.id, UserRatesBook.user_rating >= 4.0)
    )
    rated_genre_ids = db.scalars(rated_genres_stmt).all()

    # Combine and unique-ify the list
    all_target_genre_ids = list(set(fav_genre_ids) | set(rated_genre_ids))

    if not all_target_genre_ids:
        raise HTTPException(status_code=404, detail="No favorites or high ratings found to generate suggestions.")

    # 3. Find books that have ANY of these genres and haven't been rated yet
    rated_books = select(UserRatesBook.book_id).where(UserRatesBook.user_id == user.id)
    
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