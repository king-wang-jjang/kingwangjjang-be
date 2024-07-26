# from random import randint

# from app.models import user_db

# from utils import formating


# def get(limit: int, offset: int) -> list[db.User]:
#     return user_db.get(limit=limit, offset=offset)
            
# def get_by_id(id: int) -> db.User | None:
#     return user_db.get_by_id(id)
    
# def get_by_email(email: str) -> db.User | None:
#     return user_db.get_by_email(email.lower().strip())

# def create(name: str, surname: str, role: db.User.Role, email: str, password: str) -> db.User:
#     name = formating.format_string(name)
#     surname = formating.format_string(surname)
#     email = formating.format_string(email)
#     return user_db.add(name, surname, role, email)

# def update(id: int, name: str, surname: str, role: db.User.Role, email: str, password: str) -> None:
#     name = formating.format_string(name)
#     surname = formating.format_string(surname)
#     email = formating.format_string(email)
#     user_db.update(id ,name, surname, role, email)
    
# def update_name_surname(id: int, name: str, surname: str) -> None:
#     user = get_by_id(id)
#     if user is None:
#         return
    
#     name = formating.format_string(name)
#     surname = formating.format_string(surname)
#     user_db.update(
#         user.id,
#         name,
#         surname,
#         user.role,
#         user.email,
#         user.password
#     )

# def update_password(id: int, new_password: str) -> None:
#     user = get_by_id(id)
#     if user is None:
#         return
    
#     user_db.update(
#         user.id,
#         user.name,
#         user.surname,
#         user.role,
#         user.email,
#     )

# def reset_password(id: int) -> str:    
#     user = get_by_id(id)
#     if user is None:
#         return
    
#     new_password = str(randint(100000, 999999))
#     user_db.update(
#         user.id,
#         user.name,
#         user.surname,
#         user.role,
#         user.email,
#     )
    
#     return new_password
    
# def delete(id: int) -> None:
#     user_db.delete(id)
    
    