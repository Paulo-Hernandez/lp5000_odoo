import paramiko
import time
import csv
import os
import tempfile

# Diccionario para mantener el correlativo por orden de compra
correlativos = {}

def obtener_correlativo(oc):
    if oc in correlativos:
        correlativo = correlativos[oc]
        correlativo += 1
    else:
        correlativo = 1
    correlativos[oc] = correlativo
    return str(correlativo).zfill(3)

def procesar_contenido(contenido):
    bloques = contenido.split('\nT')
    bloques = [bloque + 'T' + contenido.split('T', 1)[1] for bloque in bloques[:-1]] + [bloques[-1]]
    for i, bloque in enumerate(bloques):
        print(f'Bloque {i + 1}:\n{bloque}\n')
        procesar_bloque(bloque)

def procesar_bloque(bloque):
    lineas = bloque.split('\n')
    secciones = [lineas[i:i+3] for i in range(0, len(lineas), 3)]
    for j, seccion in enumerate(secciones):
        if len(seccion) == 3:  # Asegurar que la sección tenga 3 líneas
            print(f'Sección {j + 1}:')
            print("\n".join(seccion))
            print('\n')
            datos.extend(extraer_datos_de_seccion(seccion))

def extraer_datos_de_seccion(seccion):
    try:
        oc = seccion[0][0:10]
        ticket = seccion[0][10:21]
        operario = seccion[0][21:28]
        articulo = seccion[1][0:6]
        lote = seccion[1][8:17].strip()
        fecha_ingreso = seccion[2][:8].strip()
        fecha_caducidad = seccion[2][9:17].strip()
        peso = seccion[2][17:].strip()

        return [{
            'Orden de Compra': oc,
            'Numero de Transaccion': ticket,
            'Operario': operario,
            'Codigo Articulo': articulo,
            'Lote': lote,
            'Fecha Ingreso': fecha_ingreso,
            'Fecha Caducidad': fecha_caducidad,
            'Peso': peso
        }]
    except IndexError:
        print("Error al extraer datos de la sección:", seccion)
        return []

def mostrar_y_vaciar_archivo_ssh(ip, usuario, contraseña, archivo_remoto):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip, username=usuario, password=contraseña)
        sftp_client = ssh_client.open_sftp()

        with sftp_client.open(archivo_remoto, 'r') as archivo:
            contenido = archivo.read().decode()
            if contenido:
                procesar_contenido(contenido)

                # Comentar para pruebas
                # sftp_client.open(archivo_remoto, 'w').close()
                print("El archivo se ha vaciado correctamente")
            else:
                print("El archivo está vacío")

        sftp_client.close()
        ssh_client.close()
    except FileNotFoundError:
        print("El archivo remoto no existe")
    except Exception as e:
        print(f"Error al mostrar y vaciar archivo remoto: {str(e)}")

def guardar_en_csv(datos):
    directorio_proyecto = r'C:\Users\pop_x\PycharmProjects\Lp5000_recep'
    nombre_archivo = 'ordenes_compra.csv'
    ruta_archivo = os.path.join(directorio_proyecto, nombre_archivo)

    try:
        with open(ruta_archivo, 'w', newline='') as csvfile:
            fieldnames = ['Orden de Compra', 'Numero de Transaccion', 'Operario', 'Codigo Articulo', 'Lote',
                          'Fecha Ingreso', 'Fecha Caducidad', 'Peso']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for dato in datos:
                writer.writerow(dato)

        print("Datos guardados en archivo CSV:", ruta_archivo)
    except PermissionError:
        print(f"Permiso denegado para escribir en {ruta_archivo}. Intentando con un nombre de archivo diferente.")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            with open(temp_file.name, 'w', newline='') as csvfile:
                fieldnames = ['Orden de Compra', 'Numero de Transaccion', 'Operario', 'Codigo Articulo', 'Lote',
                              'Fecha Ingreso', 'Fecha Caducidad', 'Peso']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for dato in datos:
                    writer.writerow(dato)

            print("Datos guardados en archivo CSV:", temp_file.name)

    print("Datos:", datos)

# Parámetros de conexión SSH
ip_remota = "192.168.1.100"
usuario_ssh = "ubuntupc"
contraseña_ssh = "ubuntupc"
archivo_remoto = "/home/ubuntupc/Documentos/RX02.txt"

datos = []

while True:
    mostrar_y_vaciar_archivo_ssh(ip_remota, usuario_ssh, contraseña_ssh, archivo_remoto)
    guardar_en_csv(datos)
    time.sleep(1)

