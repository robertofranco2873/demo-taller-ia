import os

# bcrypt con pocas rondas: las pruebas hashean contraseñas muchas veces.
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("JWT_SECRET", "secreto-de-pruebas-con-al-menos-32-bytes")
