import pandas as pd
from databaseModel import Book, Genre, User

def seed_test_database(session):
    # 1. Load the CSV (ensure the path is correct for your test runner)
    df = pd.read_csv('filtered_google_books.csv')

    # 2. Seed Genres from CSV
    all_genres = df['genre'].str.split(',').explode().str.strip().unique()
    for g_name in all_genres:
        if g_name and g_name.lower() != 'none':
            if not session.query(Genre).filter_by(name=g_name).first():
                session.add(Genre(name=g_name))
    session.flush()

    # 4. Seed Books from CSV
    for _, row in df.iterrows():
        new_book = Book(
            id=row['ID'],
            title=row['title'],
            author=row['author'],
            avg_rating=row['rating'] if pd.notnull(row['rating']) else 0.0
        )
        # Link genres logic here... (omitted for brevity)
        session.add(new_book)
    
    session.commit()