import xmlrpc.client

# Conexión a la instancia de Odoo
url = 'https://ingmetrica-datos-sandbox-12071743.dev.odoo.com'
db = 'ingmetrica-datos-sandbox-12071743'
username = 'aromero@ingmetrica.cl'
password = '88a302d55d70f15af3fdeda898b58102b0edc897'

# Autenticación
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

# Conexión al objeto
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))


def get_model_fields(model_name):
    try:
        # Obtener todos los campos del modelo
        fields = models.execute_kw(db, uid, password, model_name, 'fields_get', [], {'attributes': ['string', 'type']})
        return fields
    except Exception as e:
        print(f"Error: {e}")
        return None


# Ejemplo de uso
model_name = 'stock.move'  # Reemplaza con el modelo que deseas consultar
fields = get_model_fields(model_name)

if fields:
    for field, details in fields.items():
        print(f"Field: {field}, String: {details['string']}, Type: {details['type']}")
else:
    print("No se pudieron obtener los campos del modelo.")
