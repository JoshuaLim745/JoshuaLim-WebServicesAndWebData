from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import List
from passlib.context import CryptContext
import bcrypt
from databaseModel import User, Genre, get_db

router = APIRouter(prefix="/users", tags=["User CRUD"])

class UserAuth(BaseModel):
    email: EmailStr
    password: str

class GenreUpdate(UserAuth):
    mode: str  # "add" or "delete"
    genreName: str

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







@router.post("/create", summary="Register a new user")
def create_user(user_in: UserAuth, db: Session = Depends(get_db)):

    """
    ### Create User Data
    This endpoint allows you to **register a new user** in the database.
    
    * **Input**:
        * `Email`: User email
        * `Password`: User password
    * **Output**: Returns the user data upon success.
    * **Error**: Returns an appropriate message if the user already exists.
    """

    if db.query(User).filter_by(email=user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email = user_in.email,
        password = hash_password(user_in.password)  # Store the hash, NOT the plain text
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created", "email": new_user.email}






@router.post("/read", summary="View user profile")
def read_user(user_in: UserAuth, db: Session = Depends(get_db)):

    """
    ### Read User Data
    Retrieves the profile and favorite genres for an existing user.
    
    * **Input**:
        * `Email`: User email
        * `Password`: User password
    * **Security**: Serves as a basic authentication check.
    * **Output**: Returns user email and a list of their favourite genres.
    * **Error**: Returns `401 Unauthorized` if user's credentials do not match with user data in the database.
    """

    # 1. Search for the user by email ONLY
    user = db.query(User).filter_by(email=user_in.email).first()

    # 2. Check if user exists AND if the password matches the stored hash
    # verify_password(plain_text_input, hashed_password_from_db)
    if not user or not verify_password(user_in.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    return {
        "email": user.email,
        "favoriteGenres": [g.name for g in user.fav_genres]
    }






@router.put("/update-genres", summary="Modify user genre preferences")
def update_genres(data: GenreUpdate, db: Session = Depends(get_db)):


    # case sensitive check

    """
    ### Update User Preferences
    Allows a user to manage their favorite genre list.
    
    * **Input**:
        * `Email`: User email
        * `Password`: User password
        * `Mode`: Use **'add'** to add a genre to a user's favorite genre list or **'delete'** to remove it from the list.
        * `Genre name`: The name of the genre (e.g., 'Fantasy').
    * **Logic**: Modifies the `user_genre_link` association table.
    * **Output**: Returns the updated list of genres for the user.
    """

    user = db.query(User).filter_by(email=data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    genre = db.query(Genre).filter_by(name=data.genreName).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    if data.mode.lower() == "add":
        if genre not in user.fav_genres:
            user.fav_genres.append(genre)
    elif data.mode.lower() == "delete":
        if genre in user.fav_genres:
            user.fav_genres.remove(genre)
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'add' or 'delete'.")
    

    db.commit()
    return {"email": user.email, "updatedGenres": [g.name for g in user.fav_genres]}






@router.delete("/delete", summary="Remove user account")
def delete_user(user_in: UserAuth, db: Session = Depends(get_db)):

    """
    ### Delete User Data
    Permanently removes a user and their associations from the database.
    
    * **Input**:
        * `Email`: User email
        * `Password`: User password
    * **Logic**: Removes the record from the `users` table. Cascade settings handle the link table.
    * **Output**: Confirmation message of removal.
    """

    user = db.query(User).filter_by(email=user_in.email).first()
    if not user or not verify_password(user_in.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    db.delete(user)
    db.commit()
    return {"message": "User removed successfully"}