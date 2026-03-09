from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import List
from passlib.context import CryptContext
import bcrypt
from databaseModel import User, Genre, get_db
from auth import hash_password, verify_password, create_access_token, get_current_user


router = APIRouter(prefix="/users")

class UserAuth(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    email: EmailStr
    favoriteGenres: list[str]

class GenreUpdate(BaseModel):
    mode: str  # "add" or "delete"
    genreName: str


@router.post("/login", tags=["User Management"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Standard OAuth2 login flow to get a JWT token.
    * **Input**:
        * `grant_type`: Tells the server how the client is trying to authenticate. For password-based login, this should be "password".
        * `username`: User email
        * `password`: User password
        * `scope`: Send empty value as there is no role-based access control implemented
        * `client_id` and `client_secret`: Credentials used to authenticate the application itself
    * **Output**: Returns the user data upon success.
    * **Error**: Returns an appropriate message if the user provides incorrect credentials.
    
    
    """
    user = db.query(User).filter_by(email=form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}










@router.post("/create", summary="Create a new user", operation_id="createUser", tags=["User Management"])
def create_user(user_in: UserAuth, db: Session = Depends(get_db)):

    """
    ### Create User Data
    This endpoint allows you to **Create a new user** in the database.
    
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






@router.post("/read", summary="View user profile", operation_id="getUserProfile", tags=["User Management"])
def read_user_me(current_user: User = Depends(get_current_user)):

    """
    ### Read User Data
    Retrieves the profile and favorite genres for an existing user.
    
    * **Input**:
    * **Security**: Uses the token to identify and return the user profile.
    * **Output**: Returns user email and a list of their favourite genres.
    """
    
    return {
        "email": current_user.email,
        "favoriteGenres": [g.name for g in current_user.fav_genres]
    }






@router.put("/update-genres", summary="Update-genres", operation_id="updateUser", tags=["User Management"])
def update_genres(data: GenreUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    """
    ### Update User Preferences
    Allows a user to manage their favorite genre list.
    
    * **Input**:
        * `Mode`: Use **'add'** to add a genre to a user's favorite genre list or **'delete'** to remove it from the list.
        * `Genre name`: The name of the genre (e.g., 'Fantasy').
    * **Logic**: Modifies the `user_genre_link` association table.
    * **Output**: Returns the updated list of genres for the user.
    """

    genre = db.query(Genre).filter_by(name=data.genreName).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    if data.mode.lower() == "add":
        if genre not in current_user.fav_genres:
            current_user.fav_genres.append(genre)
    elif data.mode.lower() == "delete":
        if genre in current_user.fav_genres:
            current_user.fav_genres.remove(genre)
    
    db.commit()
    return {"email": current_user.email, "updatedGenres": [g.name for g in current_user.fav_genres]}
    





@router.delete("/delete", summary="Remove user account", operation_id="deleteUserAccount", tags=["User Management"])
def delete_user(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    """
    ### Delete User Data
    Permanently removes a user and their associations from the database.
    
    * **Input**: No input parameters are required as the user is identified through the token.
    * **Logic**: Removes the record from the `users` table. Cascade settings handle the link table.
    * **Output**: Confirmation message of removal.
    """
    
    db.delete(current_user)
    db.commit()
    return {"message": "User removed successfully"}
