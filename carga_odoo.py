import xmlrpc.client
import csv
import os
import pandas as pd
import logging

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.error(f"Error al buscar recepciones pendientes: {e}")
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
            producto['default_code'] = product_ref[0]['default_code'] if product_ref else 'Sin referencia'
            productos_con_referencia.append(producto)

        return productos_con_referencia

    except Exception as e:
        logger.error(f"Error al buscar productos para la recepción {recepcion_id}: {e}")
        return []


def vaciar_archivo_si_existe(ruta_archivo):
    if os.path.exists(ruta_archivo):
        with open(ruta_archivo, 'w'):
            pass
    logger.info(f"Archivo vaciado: {ruta_archivo}")


def guardar_recepciones_csv(recepciones):
    ruta_archivo_csv = 'recepciones_pendientes.csv'
    vaciar_archivo_si_existe(ruta_archivo_csv)

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

    logger.info(f"Datos guardados en archivo CSV: {ruta_archivo_csv}")


def leer_archivos_ordenes(directorio='.'):
    archivos_csv = [f for f in os.listdir(directorio) if f.startswith('ordenes_compra') and f.endswith('.csv')]
    ordenes = []
    for archivo in archivos_csv:
        df = pd.read_csv(archivo)
        df = df[df['Estado'] == 0]
        ordenes.extend(df.to_dict('records'))

    ordenes_sumadas = {}
    for orden in ordenes:
        key = (orden['Orden de Compra'], orden['Codigo Articulo'])
        if key in ordenes_sumadas:
            ordenes_sumadas[key]['Peso'] += orden['Peso']
        else:
            ordenes_sumadas[key] = {
                'Orden de Compra': orden['Orden de Compra'],
                'Codigo Articulo': orden['Codigo Articulo'],
                'Peso': orden['Peso'],
                'Estado': '0',
            }
    return list(ordenes_sumadas.values())


def actualizar_recepciones_csv(recepciones):
    ruta_archivo_csv = 'recepciones_pendientes.csv'
    vaciar_archivo_si_existe(ruta_archivo_csv)

    with open(ruta_archivo_csv, 'w', newline='') as csvfile:
        fieldnames = ['id', 'name', 'origin', 'state', 'product_id', 'product_uom_qty', 'default_code']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for recepcion in recepciones:
            writer.writerow({
                'id': recepcion['id'],
                'name': recepcion['name'],
                'origin': recepcion['origin'],
                'state': recepcion['state'],
                'product_id': recepcion['product_id'],
                'product_uom_qty': recepcion['product_uom_qty'],
                'default_code': recepcion['default_code'],
            })

    logger.info(f"Datos Actualizados en archivo CSV: {ruta_archivo_csv}")


def actualizar_estado_recepcion(recepcion_id):
    try:
        models.execute_kw(DB, uid, PASSWORD,
                          'stock.picking', 'write',
                          [[recepcion_id], {'state': 'done'}])
        logger.info(f"Estado de recepción actualizado a 'done' para ID: {recepcion_id}")
    except Exception as e:
        logger.error(f"Error al actualizar estado de recepción {recepcion_id}: {e}")


def actualizar_cantidad_recepcion(recepcion_id, producto_id, nueva_cantidad):
    try:
        # Especificar el modelo y el método 'write' para actualizar
        models.execute_kw(DB, uid, PASSWORD,
                          'stock.move', 'write',
                          [[recepcion_id], {'product_id': producto_id, 'product_uom_qty': nueva_cantidad}])
        logger.info(f"Cantidad actualizada a {nueva_cantidad} para ID de recepción: {recepcion_id} y producto ID: {producto_id}")
    except Exception as e:
        logger.error(f"Error al actualizar la cantidad para la recepción {recepcion_id} y producto ID {producto_id}: {e}")


def comparar_ordenes_con_recepciones(ordenes, recepciones):
    recepciones_a_eliminar = []

    for orden in ordenes:
        coincidencias = [recepcion for recepcion in recepciones if orden['Orden de Compra'] == recepcion['origin']]

        if coincidencias:
            for recepcion in coincidencias:
                if orden['Codigo Articulo'] == recepcion['default_code']:
                    logger.info(f"Son iguales: OC: {orden['Orden de Compra']} - Código: {orden['Codigo Articulo']}")
                    recepciones_a_eliminar.append(recepcion)
                    # Obtener la cantidad de la orden de compra
                    cantidad_orden = orden['Peso']
                    # Actualizar la cantidad en la recepción
                    actualizar_cantidad_recepcion(recepcion['id'], cantidad_orden,recepcion['default_code'])
                    # if len(coincidencias) == 1:
                        # actualizar_estado_recepcion(recepcion['id'])
                else:
                    logger.info(f"Son distintos: OC: {orden['Orden de Compra']} - Código: {orden['Codigo Articulo']}")
        else:
            logger.info(f"Son distintos: OC: {orden['Orden de Compra']} - Código: {orden['Codigo Articulo']}")

    recepciones_restantes = [recepcion for recepcion in recepciones if recepcion not in recepciones_a_eliminar]

    actualizar_recepciones_csv(recepciones_restantes)


def main():
    try:
        recepciones_pendientes = obtener_recepciones_pendientes()

        if recepciones_pendientes:
            guardar_recepciones_csv(recepciones_pendientes)
            recepciones = pd.read_csv('recepciones_pendientes.csv').to_dict('records')
            ordenes = leer_archivos_ordenes()
            comparar_ordenes_con_recepciones(ordenes, recepciones)
        else:
            logger.info("No hay recepciones pendientes.")

    except Exception as e:
        logger.error(f"Error general: {e}")


if __name__ == "__main__":
    main()

