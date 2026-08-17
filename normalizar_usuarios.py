from database import SessionLocal, Usuario


def normalizar_usuarios():

    db = SessionLocal()

    try:
        usuarios = db.query(Usuario).all()

        if not usuarios:
            print("No hay usuarios en la base de datos.")
            return

        for usuario in usuarios:

            username_original = usuario.username
            username_normalizado = username_original.strip().lower()

            # Si ya está normalizado, no hacemos nada
            if username_original == username_normalizado:
                print(
                    f"{username_original}: ya estaba normalizado"
                )
                continue

            # Comprobar que no exista otro usuario con ese nombre
            existente = db.query(Usuario).filter(
                Usuario.username == username_normalizado,
                Usuario.id != usuario.id
            ).first()

            if existente:
                print(
                    f"ERROR: no se puede convertir "
                    f"{username_original} -> {username_normalizado} "
                    f"porque ese usuario ya existe."
                )
                continue

            usuario.username = username_normalizado

            print(
                f"{username_original} -> {username_normalizado}"
            )

        db.commit()

        print("\nUsuarios normalizados correctamente.")

    except Exception as error:

        db.rollback()

        print(
            "Error normalizando usuarios:",
            error
        )

    finally:

        db.close()


if __name__ == "__main__":
    normalizar_usuarios()