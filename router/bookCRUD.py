from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from databaseModel import Book, Genre, User, UserRatesBook, book_genre_link, user_genre_link, get_db
from passlib.context import CryptContext
import bcrypt
router = APIRouter(prefix="/books", tags=["Book CRUD & rating"])



class BookSchema(BaseModel):
    title: str
    author: str
    avg_rating: float = Field(..., alias="avgRating")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class BookCreate(BookSchema):
    genre_ids: List[int] = Field(default=[], alias="genreIds")

class BookRating(BaseModel):
    email: EmailStr
    password: str
    bookId: int = Field(..., alias="bookId")
    rating: float = Field(..., ge=1.0, le=5.0)


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









@router.post("/", response_model=None, summary="Create a new book")
def create_book(book_in: BookCreate, db: Session = Depends(get_db)):

    """
    ### Create Book Record
    Adds a new book entry into the PostgreSQL `books` table and manages many-to-many genre relationships.

    * **Input**: 
        * `Title`: String name of the book.
        * `Author`: String name of the author.
        * `Avg rating`: Initial numeric rating.
        * `Genre ids`: A list of existing Genre IDs to link to this book.
    * **Logic**: 
        * Initializes the `Book` object.
        * Uses a SQL `IN` clause to fetch and link multiple genres simultaneously.
    * **Output**: Returns the full book object including the names of the associated genres.
    """

    # 1. Initialize book object
    new_book = Book(
        title=book_in.title,
        author=book_in.author,
        avg_rating=book_in.avg_rating
    )
    
    # 2. Link Genres (Many-to-Many)
    if book_in.genre_ids:
        genres = db.scalars(select(Genre).where(Genre.id.in_(book_in.genre_ids))).all()
        new_book.genres = list(genres)

    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    
    return {
        "id": new_book.id,
        "title": new_book.title,
        "author": new_book.author,
        "avgRating": new_book.avg_rating,
        "genres": [g.name for g in new_book.genres]
    }









@router.get("/{book_id}", summary="Get book details")
def read_book(book_id: int, db: Session = Depends(get_db)):
    """
    ### Read Book Details
    Fetches comprehensive information for a specific book using its unique ID.

    * **Input**: 
        * `Book ID`: The integer ID of the book in the database.
    * **Logic**: Performs a database lookup. If the ID does not exist, it triggers a `404` error.
    * **Output**: Returns the title, author, rating, and all linked genres.
    """
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "avgRating": book.avg_rating,
        "genres": [g.name for g in book.genres]
    }











@router.put("/{book_id}", summary="Update book information")
def update_book_partial(book_id: int, field_name: str, new_value: str, db: Session = Depends(get_db)):
    """
    ### Dynamic Book Update
    Updates only a single specific field for a book based on the provided name.

    * **Input**:
        * `Book ID`: The integer ID of the book in the database.
        * `Field name`: The column to change (e.g., 'title', 'author', or 'avg_rating').
        * `New value`: The new data to insert.
    * **Logic**: Uses Python's `setattr` to dynamically map the input string to the database column.
    * **Output**: Success message confirming which field was changed.
    """

    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    allowed_fields = ["title", "author", "avg_rating"]
    if field_name not in allowed_fields:
        raise HTTPException(status_code=400, detail="Invalid field.")

    try:
        # Improved dynamic conversion
        target_type = type(getattr(book, field_name))
        setattr(book, field_name, target_type(new_value))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid data type for field")

    db.commit()
    return {"message": "Update successful"}










@router.delete("/{book_id}", summary="Remove a book")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """
    ### Delete Book Record
    Permanently removes a book from the system.

    * **Input**:
        * `Book ID`: The integer ID of the book in the database.
    * **Logic**: 
        * Locates the book by ID.
        * Deletes the record; database constraints automatically clean up links in the genre association table.
    * **Error**: Returns `404 Not Found` if the book ID is invalid.
    * **Output**: A confirmation string verifying deletion.
    """
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(book)
    db.commit()
    return {"detail": f"Book {book_id} deleted"}








@router.post("/rate", summary="Rate a book")
def rate_book(data: BookRating, db: Session = Depends(get_db)):

    """ 
    ### Book Rating System
    Allows an authenticated user to assign a star rating to a specific book. This endpoint uses **Upsert** logic, meaning it handles both new ratings and updates to existing ones.
    
    * **Input**:
        * `Email`: User email
        * `Password`: User password
        * `Book ID`: The integer ID of the book in the database.
        * `Rating`: The score that a user wants to provide a book with
    * **Output**: A list of up to 3 book objects.
    * **Error State**: Returns a `400` if a rating score provided is not between 1.0-5.0
    * **Error State**: Returns a `401` if incorrect user information is provided
    * **Error State**: Returns a `404` if the book is not found in the database
    """

    # 1. FIXED AUTH: Query email then verify hash

    if not (1.0 <= data.rating <= 5.0):
        raise HTTPException(status_code=400, detail="Rating must be a number between 1.0 and 5.0")

    user = db.query(User).filter_by(email=data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Unauthorized")

    book = db.get(Book, data.bookId)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # 2. Logic for Upserting Rating
    rating_entry = db.query(UserRatesBook).filter_by(user_id=user.id, book_id=data.bookId).first()
    if rating_entry:
        rating_entry.user_rating = data.rating
    else:
        db.add(UserRatesBook(user_id=user.id, book_id=data.bookId, user_rating=data.rating))
    
    db.flush() 

    # 3. Recalculate Average
    new_avg = db.query(func.avg(UserRatesBook.user_rating)).filter(UserRatesBook.book_id == data.bookId).scalar()
    book.avg_rating = round(float(new_avg), 2)
    
    db.commit()
    return {"newBookAverage": book.avg_rating}