import paramiko
import time
import datetime
import json
import subprocess

# Diccionario para mantener el correlativo por orden de compra
correlativos = {}


def obtener_correlativo(oc):
    if oc in correlativos:
        correlativo = correlativos[oc]
        correlativo += 1
    else:
        correlativo = 1
    correlativos[oc] = correlativo
    # Ajustar el correlativo a tres dígitos con ceros a la izquierda si es necesario
    return str(correlativo).zfill(3)


def procesar_contenido(contenido):
    # Separar el contenido en bloques de 70 caracteres
    bloques = [contenido[i:i+70] for i in range(0, len(contenido), 70)]
    for bloque in bloques:
        if len(bloque) == 70:
            procesar_bloque(bloque)
        else:
            # El bloque no tiene la longitud esperada, puede ser un bloque incompleto
            # Esperar a recibir más datos
            break


def procesar_bloque(bloque):
    balanza = '02'
    oc = bloque[0:7]
    ticket = bloque[9:15]
    operario = bloque[16:22]
    articulo = bloque[23:29]
    lote = bloque[31:45].strip()
    hora_actual = datetime.datetime.now().strftime("%H%M")
    fecha = bloque[45:54].strip() + hora_actual
    fecha_caducidad = bloque[55:63] + "0000"
    peso = bloque[63:].strip()

    # Obtener el correlativo
    correlativo = obtener_correlativo(oc)

    # Construir el nombre del archivo
    nombre_archivo = f"orden_de_compra_{oc}_{correlativo}.json"

    # Ruta base del archivo
    ruta_base = r'C:\IMS\\'

    # Ruta completa del archivo
    ruta_archivo = ruta_base + nombre_archivo

    datos = {
        "Orden_de_Compra": oc,
        "Codigo": articulo,
        "Peso": peso,
        "Lote": lote,
        "Fecha_caducidad": fecha_caducidad,
        "Fecha_registro": fecha,
        "Operario": operario,
        "Bodega": "WH",
        "Operacion": "IN",
        "Balanza": balanza,
        "Ticket": ticket
    }

    # Escribir el diccionario como JSON en el archivo
    with open(ruta_archivo, 'w') as archivo_local:
        json.dump([datos], archivo_local, indent=2)

    print("Los datos se han guardado correctamente en", ruta_archivo)

    # Transferir el archivo al servidor remoto usando rsync
    destino_remoto = 'frivar@ingmetrica.odoocoop.cl:/home/frivar/IMS/recepcion'
    transferir_archivo_rsync(ruta_archivo, destino_remoto)

def transferir_archivo_rsync(origen, destino):
    comando = f'rsync -r {origen} {destino}'
    subprocess.run(comando, shell=True)


def mostrar_y_vaciar_archivo_ssh(ip, usuario, contraseña, archivo_remoto):
    try:
        # Establecer conexión SSH
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip, username=usuario, password=contraseña)

        # Crear una instancia de SFTPClient
        sftp_client = ssh_client.open_sftp()

        # Leer el contenido del archivo
        with sftp_client.open(archivo_remoto, 'r') as archivo:
            contenido = archivo.read().decode()
            if contenido:
                procesar_contenido(contenido)

                # Cerrar el archivo
                archivo.close()

                # Abrir el archivo en modo de escritura ('w') para vaciarlo
                archivo_vacio = sftp_client.open(archivo_remoto, 'w')
                archivo_vacio.close()  # Cerrar el archivo vacío

                print("El archivo se ha vaciado")
            else:
                print("El archivo está vacío")

        # Cerrar conexión SFTP
        sftp_client.close()

        # Cerrar conexión SSH
        ssh_client.close()
    except FileNotFoundError:
        print("El archivo remoto no existe")
    except Exception as e:
        print(f"Error al mostrar y vaciar archivo remoto: {str(e)}")



# Parámetros de conexión SSH
ip_remota = "192.168.1.100"
usuario_ssh = "ubuntupc"
contraseña_ssh = "ubuntupc"
archivo_remoto = "/home/ubuntupc/Documentos/RX02.txt"

# Bucle para mostrar y vaciar el archivo cada segundo
while True:
    mostrar_y_vaciar_archivo_ssh(ip_remota, usuario_ssh, contraseña_ssh, archivo_remoto)
    time.sleep(1)  # Esperar 1 segundo antes de la siguiente operación

