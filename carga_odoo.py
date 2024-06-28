import xmlrpc.client
import csv
import os
import pandas as pd

# Datos de conexión a Odoo
URL = 'https://ingmetrica-datos-sandbox-12071743.dev.odoo.com'
DB = 'ingmetrica-datos-sandbox-12071743'
USER = 'aromero@ingmetrica.cl'
PASSWORD = '88a302d55d70f15af3fdeda898b58102b0edc897'

# Conectar con la instancia de Odoo a través de XML-RPC
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
uid = common.authenticate(DB, USER, PASSWORD, {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))

def obtener_recepciones_pendientes():
    try:
        recepciones = models.execute_kw(DB, uid, PASSWORD,
                                        'stock.picking', 'search_read',
                                        [[['picking_type_id.code', '=', 'incoming'], ['state', '=', 'assigned']]],
                                        {'fields': ['id', 'name', 'origin', 'state']})
        return recepciones

    except Exception as e:
        print(f"Error al buscar recepciones pendientes: {e}")
        return []

def obtener_productos_recepcion(recepcion_id):
    try:
        productos = models.execute_kw(DB, uid, PASSWORD,
                                      'stock.move', 'search_read',
                                      [[['picking_id', '=', recepcion_id]]],
                                      {'fields': ['product_id', 'product_uom_qty']})

        productos_con_referencia = []
        for producto in productos:
            product_ref = models.execute_kw(DB, uid, PASSWORD,
                                            'product.product', 'read',
                                            [producto['product_id'][0]],
                                            {'fields': ['default_code']})
            if product_ref:
                producto['default_code'] = product_ref[0]['default_code']
            else:
                producto['default_code'] = 'Sin referencia'
            productos_con_referencia.append(producto)

        return productos_con_referencia

    except Exception as e:
        print(f"Error al buscar productos para la recepción {recepcion_id}: {e}")
        return []

def guardar_recepciones_csv(recepciones):
    ruta_archivo_csv = 'recepciones_pendientes.csv'
    with open(ruta_archivo_csv, 'w', newline='') as csvfile:
        fieldnames = ['id', 'name', 'origin', 'state', 'product_id', 'product_uom_qty', 'default_code']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for recepcion in recepciones:
            productos = obtener_productos_recepcion(recepcion['id'])
            for producto in productos:
                writer.writerow({
                    'id': recepcion['id'],
                    'name': recepcion['name'],
                    'origin': recepcion['origin'],
                    'state': recepcion['state'],
                    'product_id': producto['product_id'][0],
                    'product_uom_qty': producto['product_uom_qty'],
                    'default_code': producto['default_code']
                })

    print(f"Datos guardados en archivo CSV: {ruta_archivo_csv}")

def leer_archivos_ordenes(directorio='.'):
    archivos_csv = [f for f in os.listdir(directorio) if f.startswith('ordenes_compra') and f.endswith('.csv')]
    ordenes = []
    for archivo in archivos_csv:
        df = pd.read_csv(archivo)
        ordenes.extend(df.to_dict('records'))
    return ordenes

def comparar_ordenes_con_recepciones(ordenes, recepciones):
    for orden in ordenes:
        for recepcion in recepciones:
            if orden['Orden de Compra'] == recepcion['origin'] and orden['Codigo Articulo'] == recepcion['default_code']:
                print(f"Son iguales: OC: {orden['Orden de Compra']} - Código: {orden['Codigo Articulo']}")
            else:
                print(f"Son distintos: OC: {orden['Orden de Compra']} - Código: {orden['Codigo Articulo']}")

def main():
    try:
        recepciones_pendientes = obtener_recepciones_pendientes()

        if recepciones_pendientes:
            guardar_recepciones_csv(recepciones_pendientes)
            recepciones = pd.read_csv('recepciones_pendientes.csv').to_dict('records')
            ordenes = leer_archivos_ordenes()
            comparar_ordenes_con_recepciones(ordenes, recepciones)
        else:
            print("No hay recepciones pendientes.")

    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    main()




