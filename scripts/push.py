from py_vapid import Vapid
vapid = Vapid()
vapid.generate_keys()
print("Public:", vapid.public_key.decode('utf-8'))
print("Private:", vapid.private_key.decode('utf-8'))