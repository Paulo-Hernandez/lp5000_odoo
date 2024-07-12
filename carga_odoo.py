import xmlrpc.client
import csv
import os
import pandas as pd
import logging
import time

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def leer_configuracion(archivo):
    config_odoo = {}
    with open(archivo, 'r') as file:
        for line in file:
            key, value = line.strip().split('=')
            config_odoo[key] = value
    return config_odoo


config = leer_configuracion('config_odoo.txt')
URL = config['URL']
DB = config['DB']
USER = config['USER']
PASSWORD = config['PASSWORD']

# Conectar con la instancia de Odoo a través de XML-RPC
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
uid = common.authenticate(DB, USER, PASSWORD, {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))


def filtrar_recepciones_por_id(recepciones, id_filtrar):
    recepciones_filtradas = [recepcion for recepcion in recepciones if recepcion['id'] == id_filtrar]

    return bool(recepciones_filtradas)


def obtener_id_producto_por_referencia(referencia_interna):
    try:
        # Buscar el producto por su referencia interna
        producto = models.execute_kw(DB, uid, PASSWORD,
                                     'product.product', 'search_read',
                                     [[['default_code', '=', referencia_interna]]],
                                     {'fields': ['id', 'default_code'], 'limit': 1})
        if producto:
            producto_id = producto[0]['id']
            logger.info(f"ID del producto con referencia interna '{referencia_interna}': {producto_id}")
            return producto_id
        else:
            logger.warning(f"No se encontró producto con referencia interna '{referencia_interna}'")
            return None
    except Exception as e:
        logger.error(f"Error al obtener el ID del producto con referencia interna '{referencia_interna}': {e}")
        return None


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

    if not archivos_csv:
        # logger.info("No se encontraron archivos 'ordenes_compra'.")
        return

    archivo = archivos_csv[0]

    try:
        df = pd.read_csv(os.path.join(directorio, archivo))
    except pd.errors.EmptyDataError:
        logger.info(f"El archivo {archivo} está vacío.")
        os.remove(os.path.join(directorio, archivo))
        return

    if df.empty:
        logger.info(f"El archivo {archivo} no contiene datos.")
        os.remove(os.path.join(directorio, archivo))
        return

    df = df[df['Estado'] == 0]

    if df.empty:
        logger.info(f"El archivo {archivo} no contiene órdenes con 'Estado' igual a 0.")
        os.remove(os.path.join(directorio, archivo))
        return

    ordenes = df.to_dict('records')
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
                'Lote': str(orden['Lote']).zfill(14)
            }
    ordenes_sumadas_values = list(ordenes_sumadas.values())
    logger.info("Ordenes procesadas y enviadas")
    os.remove(os.path.join(directorio, archivo))
    logger.info(f"El archivo {archivo} ha sido eliminado.")

    return ordenes_sumadas_values


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


def actualizar_cantidad_recepcion(recepcion_id, producto_id, nueva_cantidad, lote):
    try:

        move_ids = models.execute_kw(DB, uid, PASSWORD,
                                     'stock.move', 'search',
                                     [[['picking_id', '=', recepcion_id]]])

        producto_id = obtener_id_producto_por_referencia(producto_id)

        # Leer los campos 'id' y 'product_id' de los movimientos de stock
        moves = models.execute_kw(DB, uid, PASSWORD,
                                  'stock.move', 'read',
                                  [move_ids], {'fields': ['id', 'product_id']})

        # Crear un diccionario con los IDs de los movimientos y los IDs de los productos
        move_dict = {move['id']: move['product_id'][0] for move in moves}

        # Encontrar el ID del stock.move que contiene el product_id deseado
        id_move = None
        for move_id, prod_id in move_dict.items():
            if prod_id == producto_id:
                id_move = move_id
                break

        move_line_ids = models.execute_kw(DB, uid, PASSWORD, 'stock.move.line', 'search', [[['move_id', '=', id_move]]])
        if not move_line_ids:
            logger.error(f"No se encontraron líneas de movimiento para el movimiento con ID {id_move}.")

            # Actualizar cada línea de movimiento con el lote
        for move_line_id in move_line_ids:
            models.execute_kw(DB, uid, PASSWORD, 'stock.move.line', 'write', [[move_line_id], {
                'lot_name': lote,
            }])
            logger.info("Actualizacion de lote")

        # Especificar el modelo y el método 'write' para actualizar
        models.execute_kw(DB, uid, PASSWORD,
                          'stock.move', 'write',
                          [[id_move], {'product_id': producto_id, 'quantity': nueva_cantidad}])
        logger.info(
            f"Cantidad actualizada a {nueva_cantidad} para ID de recepción: {recepcion_id} "
            f"y producto ID: {producto_id}")

    except Exception as e:
        logger.error(
            f"Error al actualizar la cantidad para la recepción {recepcion_id} y producto ID {producto_id}: {e}")


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

                    # Obtener el lote por producto
                    lote_orden = orden['Lote']

                    # Actualizar la cantidad en la recepción
                    actualizar_cantidad_recepcion(recepcion['id'],
                                                  recepcion['default_code'],
                                                  cantidad_orden,
                                                  lote_orden)

                    if len(coincidencias) == 1:
                        actualizar_estado_recepcion(recepcion['id'])

                else:
                    logger.info(f"Son distintos: OC: {orden['Orden de Compra']} - Código: {orden['Codigo Articulo']}")
        else:
            logger.info(f"Son distintos: OC: {orden['Orden de Compra']} - Código: {orden['Codigo Articulo']}")

    recepciones_restantes = [recepcion for recepcion in recepciones if recepcion not in recepciones_a_eliminar]

    actualizar_recepciones_csv(recepciones_restantes)


def main():
    try:
        if recepciones_pendientes:
            recepciones = pd.read_csv('recepciones_pendientes.csv').to_dict('records')
            ordenes = leer_archivos_ordenes()
            if ordenes:
                comparar_ordenes_con_recepciones(ordenes, recepciones)
            # else:
                # logger.info("No hay ordenes pendientes.")
        else:
            logger.info("No hay recepciones pendientes.")

    except Exception as e:
        logger.error(f"Error general: {e}")


if __name__ == "__main__":
    recepciones_pendientes = obtener_recepciones_pendientes()
    logger.info("INICIO DE CICLO")
    if recepciones_pendientes:
        guardar_recepciones_csv(recepciones_pendientes)
    while True:
        main()
        time.sleep(1)
