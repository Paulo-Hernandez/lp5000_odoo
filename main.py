import paramiko
import time
import csv
from datetime import datetime


def leer_configuracion(config_file_lp):
    config_lp = {}
    with open(config_file_lp, 'r', encoding='ascii') as file:
        for line in file:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                config_lp[key.strip()] = value.strip()
    return config_lp


def procesar_contenido(contenido):
    bloques = []
    bloque_actual = []

    lineas = contenido.splitlines()

    for linea in lineas:
        if linea.startswith('OCP'):
            if bloque_actual and bloque_actual[-1].startswith('T'):
                bloques.append(bloque_actual)
                bloque_actual = []
        bloque_actual.append(linea)
        if linea.startswith('T'):
            bloques.append(bloque_actual)
            bloque_actual = []

    # Asegúrate de agregar el último bloque solo si es completo
    if bloque_actual and bloque_actual[-1].startswith('T'):
        bloques.append(bloque_actual)

    for i, bloque in enumerate(bloques):
        print(f"Bloque {i + 1}:")
        for linea in bloque:
            print(linea)
        print()

    return bloques


def verificar_linea_t(contenido):
    lineas = contenido.splitlines()
    for linea in lineas:
        if linea.startswith('T'):
            return True
    return False


def mostrar_y_vaciar_archivo_ssh(ip, usuario, contrasena, ruta_archivo_remoto_lp):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip, username=usuario, password=contrasena)

        sftp_client = ssh_client.open_sftp()
        with sftp_client.open(ruta_archivo_remoto_lp, 'r') as archivo_remoto:
            contenido = archivo_remoto.read().decode('ascii', errors='ignore')
            if verificar_linea_t(contenido):
                fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
                ruta_destino_local = f'C:\\Users\\ingmP\\PycharmProjects\\lp5000_odoo\\02_copia_{fecha_actual}.txt'

                with open(ruta_destino_local, 'w', encoding='ascii') as archivo_local:
                    archivo_local.write(contenido)

                if contenido:
                    bloques = procesar_contenido(contenido)
                    bloques_completos = [bloque for bloque in bloques if bloque[-1].startswith('T')]
                    if bloques_completos:
                        segmentos = procesar_segmentos(bloques_completos)
                        guardar_en_csv(segmentos)

                        # Borrar las líneas desde la línea con 'T' hacia arriba en el archivo remoto
                        contenido_modificado = borrar_lineas_procesadas(contenido)
                        with sftp_client.open(ruta_archivo_remoto_lp, 'w') as archivo_remoto_modificado:
                            archivo_remoto_modificado.write(contenido_modificado)
                    else:
                        print("No hay bloques completos para procesar")
            else:
                print("No hay líneas de totales en el archivo remoto")

        sftp_client.close()
        ssh_client.close()
    except FileNotFoundError:
        print("El archivo remoto no existe")
    except Exception as e:
        print(f"Error general: {str(e)}")


def borrar_lineas_procesadas(contenido):
    lineas = contenido.splitlines()
    index_t = -1
    for i, linea in enumerate(lineas):
        if linea.startswith('T'):
            index_t = i
            break
    if index_t != -1:
        lineas_modificadas = lineas[index_t + 1:]  # Mantener las líneas después de la línea que empieza con 'T'
    else:
        lineas_modificadas = lineas
    return "\n".join(lineas_modificadas) + "\n"


def procesar_segmentos(bloques):
    segmentos = []
    for i, bloque in enumerate(bloques):
        for j in range(0, len(bloque), 3):
            segmento = bloque[j:j + 3]
            segmentos.append((i + 1, j // 3 + 1, segmento))
    return segmentos


def guardar_en_csv(segmentos):
    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
    ruta_archivo_csv = f'C:\\Users\\ingmP\\PycharmProjects\\lp5000_odoo\\ordenes_compra_{fecha_actual}.csv'
    with open(ruta_archivo_csv, 'w', newline='', encoding='ascii') as csvfile:
        fieldnames = ['Bloque', 'Segmento', 'Orden de Compra', 'Numero de Transaccion', 'Operario', 'Codigo Articulo',
                      'Lote', 'Fecha Ingreso', 'Fecha Caducidad', 'Peso']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for bloque_num, segmento_num, segmento in segmentos:
            if len(segmento) < 3:
                continue
            oc = segmento[0][2:9]
            transaccion = segmento[0][12:17]
            operario = segmento[0][23:30]
            codigo_articulo = segmento[1][0:6]
            lote = segmento[1][8:].strip()
            fecha_ingreso = segmento[2][0:8]
            peso = segmento[2][10:].strip()

            writer.writerow({
                'Bloque': bloque_num,
                'Segmento': segmento_num,
                'Orden de Compra': oc,
                'Numero de Transaccion': transaccion,
                'Operario': operario,
                'Codigo Articulo': codigo_articulo,
                'Lote': lote,
                'Fecha Ingreso': fecha_ingreso,
                'Peso': peso
            })

    print(f"Datos guardados en archivo CSV: {ruta_archivo_csv}")


# Leer configuración desde el archivo config_lp.txt
config_file = 'config_lp.txt'
config = leer_configuracion(config_file)

ip_remota = config.get('ip_remota')
usuario_ssh = config.get('usuario_ssh')
contrasena_ssh = config.get('contrasena_ssh')
ruta_archivo_remoto = config.get('ruta_archivo_remoto')

while True:
    mostrar_y_vaciar_archivo_ssh(ip_remota, usuario_ssh, contrasena_ssh, ruta_archivo_remoto)
    time.sleep(1)  # Esperar antes de la próxima operación
