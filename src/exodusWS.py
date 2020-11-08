# -*- coding: utf-8 -*-
#Carga de librerías
import time
from bs4 import BeautifulSoup
import regex as re
import requests
import json
from skimage import io, transform
import numpy as np
import matplotlib.pyplot as plt
import sys

def cargarElementosTratados(rutaDataSet):
    """
    Created on Sun Nov 01 14:00:00 2020
    Se encargaq de cargar el json del dataset actual en un diccionario y devolver en una lista, aquellos elementos ya tratados en base a su atributo Id
  
    @author: luimoco

    Entrada:  rutaDataSet: Se establece la ruta del entorno de ejecución donde está almacenado el Json con el dataset actual

    Salida: data_dict: La información completa de todos los elementos tratados, para poder añadir los elmeentos tratados en la sesión.
            data_list: La lista de los Id ya tratados, para que el proceso no los rastree en la sesión.
    """
    try:
        with open(rutaDataSet) as json_file: 
            data_dict = json.load(json_file)
            data_list = [int(x) for x in data_dict]
    except Exception:
        data_dict = {}
        data_list = []

    return data_dict, data_list 

def crearListaElementosATratar(tratados, inicio = 1, limite = 100):
    """
    Created on Fri Oct 30 19:36:00 2020
    Devuelve una lista de enteros para iterar con aquellos elementos que no han sido tratados previamente o se han tratado con error desde un número inicial hasta un límite fijado.

    @author: luimoco

    Entrada:  tratados: De esta lista se obtiene información de los elementos están ya tratados.
            inicio: Establece el id para comenzar a iterar.
            limite: Establece un límite, marcado desde el inicio, para la iteración de rastreo.

    Salida: Una lista de identificadores de elementos y que no hayan sido tratados previamente
    """

    lista = list(range(inicio, inicio + limite))
    return [x for x in lista if x not in tratados]

    return lista

def gestionarTiempos(motivo = 'ESPERA_ESTANDAR', intento = 1):
    """
    Created on Fri Oct 30 19:41:00 2020
    Herramienta para la gestión temporal del user-agent, a acelerando o frenando el ritmo de ejecución a partir de eventos producidos durante el proceso.

    @author: luimoco

    Entrada:motivo: Indicador del evento producido en el rastreador
            intento: Señala el intento actual de recuperación de la página que servirá de multiplicador para esperar más o menos tiempo.
    """
    MOTIVOS = {'ESPERA_ESTANDAR':3,
               'ESPERA_ERROR_CONEXION':3600,
               'ESPERA_TIMEOUT':300,
               'ESPERA_ERROR_SERVIDOR':3600,
               'ESPERA_ERROR_CLIENTE':5,
               'ESPERA_CORRECTA_INCIDENCIAS':10}
    
    retraso = MOTIVOS[motivo] * intento
    
    time.sleep(retraso)
    
def obtenerIcono(ruta):
    """
    Created on Fri Nov 01 14:11:00 2020
    Devuelve la imagen procesada del icono de la aplicación obtenido desde el servidor a través de la ruta que se obtiene del rastreo de la página donde está contenida la imagen.

    @author: luimoco
    
    Entrada: ruta: El atributo src obtenido en el rastreo de la página para poder conformar la URL desde la que rescatar la imagen desde el servidor.
    
    Salida: icono: La imagen procesada en un formato que se pueda tratar por un dataset.
                   Se devuelve una lista de 32*32 elementos, donde cada elemento es un pixel representado por otra lista de 4
                   elementos correspondientes a los componentes RGBA.
                   Para visualizar la imagen hay que volver a redimensionarla a 32,32,4, transformarla en array de numpy y
                   dibujarla con plt.imshow > plt.imshow(np.array(icon).reshape(32,32,4))
            error: Si se ha producido un error, se devuelve el mensaje para poder incluirlo en el tratamiento de errores de la página.
    """
    
    URL_BASE = 'https://reports.exodus-privacy.eu.org/es'
    ruta = URL_BASE + ruta + '/'
    try:
        photo = (transform.resize(io.imread(ruta), (32, 32), mode='edge') * 255).astype(np.uint8)
        if len(photo.shape) == 2: #Tratamiento cuando la imagen solo tiene el canal de transparencia
            rgba = np.full((32,32,4), 0).astype(np.uint8)
            for i in range (0,32):
                for j in range (0,32):
                    if photo[i][j] == 0:
                        rgba[i][j][0] = 255
                        rgba[i][j][1] = 255
                        rgba[i][j][2] = 255
                        rgba[i][j][3] = 0
                    else:
                        rgba[i][j][3] = 255 - photo[i][j]
            photo = rgba
        if photo.shape[2] == 3: #Tratamiento para añadir el canal alpha si la foto original no tenía transparencias
            rgba = np.full((32,32,4), 255)
            rgba[:,:,0] = photo[:,:,0]
            rgba[:,:,1] = photo[:,:,1]
            rgba[:,:,2] = photo[:,:,2]
            photo = rgba
        
        icono = photo.reshape(-1,4).tolist()
        error = ''
    except Exception as e:
        icono = []
        error = str(e)
    
    return icono, error

def rastrearHtml(html, iconoAFichero):
    """
    Created on Fri Oct 30 22:30:00 2020
    Módulo principal para el proceso de extracción de los atributos del dataset a partir de la página web solicitada al servidor.
    Se añade una gestión de los posibles errores producidos para poder afinar la herramienta de rastreo.

    @author: luimoco

    Entrada: html: Contenido de la request de la página del elemento a rastrear.
             iconoAFichero: Indicador si el dataset contendrá el atributo icono o se guardará en un fichero aparte.
  
    Salida: atributos: Se trata de un diccionario clave/valor con los atributos que se quieren recuperar y su valor. Su estructura esté preparda para poder almacenar de una manera
                       directa la información en un formato Json.
                       {
                          'Id' : id,
                          'Name' : 'nombre'
                          'Tracker_count' : cuenta_rastreadores,
                          'Permissions_count' : cuenta_permisos,
                          'Version' : 'versión',
                          'Downloads' : 'descargas',
                          'Analysis_date': 'analysis_date',
                          'Trackers' : [{'nombre_rastreador' : ['propósito']}]
                          'Permissions' : ['permisos']
                          'Permissions_warning_count' : cuenta_permisos_críticos
                          'Country' : 'país'
                          'Developer' : 'desarrollador'
                          'Icon' : [[RGBA]] << En el caso de iconoAFichero == False
                        }

            error: Información del atributo cuya recuperación ha provocado el error y su fallo para poder investigarlo posteriormente. En el caso que un atributo falle, se incorporará
                   un valor desconocido 'na'
    """
    atributos = {}
    error = {}

    soup = BeautifulSoup(html, features='lxml')
  
    #Id de la aplicación
    try:
        tag = soup.find('input', {'name': 'next'})
        appId = tag['value'].split('/')[2]
        atributos['Id'] = int(appId)
    except Exception as e:
        error['Id'] = str(e)
        atributos['Id'] = 'na'

    #Nombre
    try:
        tag = soup.h1
        atributos['Name'] = str.strip(tag.string)
    except Exception as e:
        error['Name'] = str(e)
        atributos['Name'] = 'na'

    #Número de rastreadores
    try:
        it_tag = soup.find('a', {'href': '#trackers'})
        for tag in it_tag.children:
            if tag.name == 'span':
                atributos['Tracker_count'] = int(tag.string)
    except Exception as e:
        error['Tracker_count'] = str(e)
        atributos['Tracker_count'] = 'na'

    #Número de permisos
    try:
        it_tag = soup.find('a', {'href': '#permissions'})
        for tag in it_tag.children:
            if tag.name == 'span':
                atributos['Permissions_count'] = int(tag.string)
    except Exception as e:
        error['Permissions_count'] = str(e)
        atributos['Permissions_count'] = 'na'

    #Versión, descargas y fecha de análisis
    try:
        meses = {'Enero':'01','Febrero':'02','Marzo':'03','Abril':'04','Mayo':'05','Junio':'06','Julio':'07','Agosto':'08','Septiembre':'09','Octubre':'10','Noviembre':'11','Diciembre':'12'}
        it_tag = soup.find_all('div', {'class':'col-md-8 col-12'})
        for tag in it_tag: #recorrer las etiquetas <div class = "col-md-8 col-12"> hasta encontrar la que aloja la versión, descargas y fecha de análisis.
            if 'Versión' in tag.text:
                descr = tag.text
                break
        
        if 'Versión' in descr:
            atributos['Version'] = re.search(r'([0-9]*\.)+[0-9]*', descr).group()
        else:
            atributos['Version'] = 'na'
        if 'Descargas' in descr:
            atributos['Downloads'] = re.search(r'Descargas: ([0-9]*(,[0-9]+)*(\+)*)', descr).group(1) or ''
        else:
            atributos['Downloads'] = 'na'
    except Exception as e:
        error['VersionDownloads'] = str(e)
        atributos['Version'] = 'na'
        atributos['Downloads'] = 'na'
    try:
        fecha = re.search(r'creado el ([0-9]{1,2}) de (.*?) de ([0-9]{4})', descr)
        atributos['Analysis_date'] = fecha.group(1) + '-' + meses[fecha.group(2)] + '-' + fecha.group(3)
    except Exception as e:
        error['Analysis_date'] = str(e)
        atributos['Analysis_date'] = 'na'

    #Trackers
    try:
        it_tag = soup.find_all('div', {'class':'col-md-8 col-12'})
        for rastreadores in it_tag: #recorrer las etiquetas <div class = "col-md-8 col-12"> hasta encontrar la que aloja los rastreadores.
            if 'rastreadores en la aplicación' in rastreadores.text:
                break
    
        trackers = [] 
        for tag in rastreadores.children:
            if str(type(tag)) == "<class 'bs4.element.Tag'>": #Cuando es una etiqueta BS4 y no un texto
                if (tag.name == 'p') and (len(tag.attrs) > 0): #Los rastreadores se encuentran en las etiqueta <p> con atributos
                    nombre = next(tag.children).string #El nombre del rastreador se encuentra en el primer hijo de la etiqueta <p> (es el texto de <a>)
                    info_propositos = tag.next_sibling #Si hay propósitos, se encuentran en el primer hermano de la etiqueta <p> (distintos <span>)
                    if info_propositos.name != 'span': #Tratamiento para los casos en los que <span> no es hermano directo de <p> por contener un texto.
                        info_propositos = tag.next_sibling.next_sibling
                    propositos = []
                    if info_propositos.string != '': #Si el rastreador tiene propósitos registrados
                        for proposito in info_propositos.find_all('span'): #Se recorren los propósitos que son el texto de cada etiqueta <span>
                            propositos.append(proposito.string)
                    trackers.append({nombre:propositos})
        atributos['Trackers'] = trackers
    except Exception as e:
        error['Trackers'] = str(e)
        atributos['Trackers'] = []

    #Permisos y permisos preligrosos
    try:
        it_tag = soup.find_all('div', {'class':'col-md-8 col-12'})
        for bloquePermisos in it_tag: #recorrer las etiquetas <div class = "col-md-8 col-12"> hasta encontrar la que aloja los permisos.
            if 'permisos en la aplicación' in bloquePermisos.text:
                break
    
        permisos = []
        it_permisos = bloquePermisos.find_all('span', {'data-placement':'top'})
        for permiso in it_permisos: #Para cada etiqueta <span data-placement = "top">, añadir su texto si no se encuentra repetido.
            if permiso.text not in permisos:
                permisos.append(permiso.text)
        atributos['Permissions'] = permisos

        atributos['Permissions_warning_count'] = len(bloquePermisos.find_all('img',{'title':'Protection level: dangerous'}))
    except Exception as e:
        error['Tracker_countPermissions_warning_count'] = str(e)
        atributos['Permissions'] = []
        atributos['Permissions_warning_count'] = 'na'


    #País, desarrollador
    try:
        for tag in soup.find_all('b'): #recorrer las etiquetas <b> hasta encontrar la que aloja la información del Emisor de la app.
            if 'Emisor:' in tag.text:
                break
        #La información del Emisor la rellena cada programador de apps libremente, por lo que algunos de los datos no tendrán una calidad deseable.
        emisor = tag.next_sibling.next_sibling.text
        if '=' in tag.next_sibling.next_sibling.text: #Hay información de emisores que se codifica con clave = valor
            if 'organizationName=' in emisor:
                if ',' in emisor[emisor.find('organizationName=')+17:]: #Tratamiento para incluir el carácter ',' en organizaciones cuyo nombre lo contenga. Ej. Google, Inc.
                    atributos['Developer'] = emisor[emisor.find('organizationName=')+17:][:emisor[emisor.find('organizationName=')+17:].find(',')]
                else:
                    atributos['Developer'] = emisor[emisor.find('organizationName=')+17:]
            else:
                atributos['Developer'] = 'na'
            if 'countryName=' in emisor:
                if ',' in emisor[emisor.find('countryName=')+12:]: #Tratamiento para incluir el carácter ',' en países.
                    atributos['Country'] = atributos['Country'] = emisor[emisor.find('countryName=')+12:][:emisor[emisor.find('countryName=')+12:].find(',')]
                else:
                    atributos['Country'] = atributos['Country'] = emisor[emisor.find('countryName=')+12:]
            else:
                atributos['Country'] = 'na'
        if ':' in tag.next_sibling.next_sibling.text:  #Hay información de emisores que se codifica con clave : valor
            if 'Organization:' in emisor:
                if ',' in emisor[emisor.find('Organization:')+14:]: #Tratamiento para incluir el carácter ',' en organizaciones.
                    atributos['Developer'] = atributos['Developer'] = emisor[emisor.find('Organization:')+14:][:emisor[emisor.find('Organization:')+14:].find(',')]
                else:
                    atributos['Developer'] = atributos['Developer'] = emisor[emisor.find('Organization:')+14:]
            else:
                atributos['Developer'] = 'na'
            if 'Country:' in emisor:
                if ',' in emisor[emisor.find('Country:')+9:]: #Tratamiento para incluir el carácter ',' en países.
                      atributos['Country'] = atributos['Country'] = emisor[emisor.find('Country:')+9:][:emisor[emisor.find('Country:')+9:].find(',')]
                else:
                    atributos['Country'] = atributos['Country'] = emisor[emisor.find('Country:')+9:]
            else:
                atributos['Country'] = 'na'
    except Exception as e:
        error['CountryDeveloper'] = str(e)
        atributos['Country'] = 'na'
        atributos['Developer'] = 'na'

    #Icono
    ruta = soup.find('img',{'class':'rounded'})['src']
    icono, fallo = obtenerIcono(ruta)
    
    if fallo == '':
        if iconoAFichero == True: #Si preferimos un dataset con ficheros de imágen se guardan en la misma ruta.
            plt.axis('off')
            plt.imshow(np.array(icono).reshape(32,32,4))
            plt.savefig((appId + '.png'))
            plt.clf()
        else: #Si preferimos un dataet con la imagen RGBA integrada, se incluye en el atributo.
            atributos['icon'] = icono
    else:
        error['Icon'] = fallo
        if iconoAFichero == False:
            atributos['Icon'] = 'na'

    return atributos, error

def rastreo(inicio, limite, iconoAFichero):
    #Inicializar cabecera del user-agent
    HEADER = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, sdch, br",
        "Accept-Language": "en-US,en;q=0.8",
        "Cache-Control": "no-cache",
        "dnt": "1",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36"
    }
    MAX_REINTENTOS = 10 #Veces que se intenta procesar la misma web
    MAX_REINTENTOS_404 = 3 #Sucesión de webs con más de 10 errores 404 que permitimos. Sirve para parar el rastreador cuando se ha llegado al final de los informes existentes y evitar trampa de araña
    TOLERANCIA_ERRORES = 3 #Marca el número máximo de atributos con valor 'na' que podrá contener cada elemento. Si se supera, no se incorpora al dataset.
    URL_BASE = 'https://reports.exodus-privacy.eu.org/es/reports/'
    FICHERO_ICONO_INTEGRADO = 'exodus.json'
    FICHERO_ICONO_A_FICHERO = 'exodusNoIcon.json'
    
    #Inicializar el fichero exodus a utilizar.
    if iconoAFichero == False:
        fichero = FICHERO_ICONO_INTEGRADO
    else:
        fichero = FICHERO_ICONO_A_FICHERO

    #Inicializar lista de los elementos ya tratados a partir del json del dataset.
    tratados_dict, tratados_list = cargarElementosTratados(fichero)
    #Inicializar intentos
    intento = 1
    #Inicializar intentos 404
    intento404 = 1
    #Inicializar repetición
    repeticion = True
    #Inicializar índice de elementos
    elem = 0
    #Inicializar incidencias
    incidencias = {}
    
    #Crear lista de elementos a tratar(Serie_elementos_tratados, inicio, limite)
    lista = crearListaElementosATratar(tratados_list, inicio, limite)
    #Crear el diccionario donde se recogeran los elementos procesados de la sesión.
    scrap_json = {}
    
    while elem < len(lista) and intento <= MAX_REINTENTOS and repeticion == True: #Mientras existan elementos en la lista, durante un número marcado de reintentos y si no se para la extracción
        web = None
        url = URL_BASE + str(lista[elem]) + '/'
    
        try: #Manejo de posibles excepciones causadas por la petición de la página gestionando tiempos, repeticiones o paradas
            web = requests.get(url, headers = HEADER)
        except requests.exceptions.ConnectionError as e:
            gestionarTiempos('ESPERA_ERROR_CONEXION', intento)
            print('Error de conexión procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '.\n\t' + str(e))
            repeticion = True
        except requests.exceptions.ConnectTimeout as e:
            gestionarTiempos('ESPERA_TIMEOUT', intento)
            repeticion = True
            print('Error de conexión procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '.\n\t' + str(e))
        except requests.exceptions.ProxyError as e:
            repeticion = False
            print('Error fatal de proxy procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '. Rastreo parado.\n\t' + str(e))
        except requests.exceptions.SSLError as e:
            repeticion = False
            print('Error fatal de SSL procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '. Rastreo parado.\n\t' + str(e))
        except Exception as e:
            repeticion = False
            print('Error fatal no controlado procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '. Rastreo parado.\n\t' + str(e))
    
        if web != None: #Si se ha recuperado información del servidor, comprobamos su status.
            if (web.status_code >= 500) and (web.status_code < 600): #Errores en el servidor
                print('Error ' + str(web.status_code) + ' de servidor producido en la request procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '.')
                gestionarTiempos('ESPERA_ERROR_SERVIDOR', intento)
                repeticion = True
                if intento < MAX_REINTENTOS:
                    intento += 1
                else:
                    intento = 1
                    elem += 1
            if (web.status_code >= 400) and (web.status_code < 500): #Errores en el cliente > Avisar y volvemos a intentarlo tras un tiempo hasta agotar intentos y pasar al siguiente
                print('Error ' + str(web.status_code) + ' de cliente producido en la request procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '.')
                gestionarTiempos('ESPERA_ERROR_CLIENTE', intento)
                repeticion = True
                if intento < MAX_REINTENTOS:
                    intento += 1
                else:
                    if intento404 < MAX_REINTENTOS_404:
                        intento = 1
                        intento404 += 1
                        elem += 1
                    else:
                        break
            if (web.status_code >= 300) and (web.status_code < 400): #Errores de redirección > Paramos el rastreo de esta url y seguimos.
                print('Error ' + str(web.status_code) + ' de redirección en la request procesando ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '. Rastreo parado.')
                repeticion = False
                intento = 1
                elem += 1
            if (web.status_code > 200) and (web.status_code < 300): #Petición correcta con incidencias > Avisar y volvemos a intentarlo tras un tiempo hasta agotar intentos y pasar al siguiente.
                print('Incidencia ' + str(web.status_code) + ' tras petición correcta procesando  ' + url + '\n\tIntento ' + str(intento) + ' de ' + str(MAX_REINTENTOS) + '.')
                gestionarTiempos('ESPERA_CORRECTA_INCIDENCIAS', intento)
                repeticion = True
                if intento < MAX_REINTENTOS:
                    intento += 1
                else:
                    intento = 1
                    elem += 1
            if web.status_code == 200: #Petición correcta y html a nuestra disposición
                app, error = rastrearHtml(web.content, iconoAFichero)
                if app != None: #Si se ha procesado la web correctamente y extraído la información
                    if len(error) > TOLERANCIA_ERRORES: #Tolerancia a errores, solo se registran como incidencia los elementos que superan la tolerancia. Si no la superan, quedan registrados con sus na donde fallara.
                        incidencias[str(lista[elem])] = error
                    else:
                        scrap_json[str(lista[elem])] = app
                        incidencias[str(lista[elem])] = error
                    elem += 1
                    intento = 1
                    print('Rastreada url ' + url + ' con éxito')
                    gestionarTiempos('ESPERA_ESTANDAR', intento)
                else: #Si no se ha procesado por un fallo del parseador del html se apunta la incidencia y se procede con el siguiente
                    incidencias[str(lista[elem])] = error
                    elem += 1
                    intento = 1
        else: #Si no se ha recuperado información del servidor
            if intento < MAX_REINTENTOS: #Si no se ha excedido el número de reintentos > se intenta de nuevo
                intento += 1
            else: #Si se ha pasado el número de intentos, se avanza al siguiente.
                intento = 1
                elem += 1
    
    print('Rastreo finalizado')
    #Actualizar el diccionario de los elmentos ya tratados con los rastreados en esta sesión y guardar el dataset y las incidencias
    tratados_dict.update(scrap_json)
    
    try:
        with open(fichero, 'w') as outfile: #Al acabar, volcar el nuevo fichero con el dataset.
            json.dump(tratados_dict, outfile)
        
        with open(('incidencias_' + str(inicio) + '_' + str(inicio + limite - 1) + '.json'), 'w') as outfile: #Al acabar, volcar el fichero de incidencias
            json.dump(incidencias, outfile)
    except Exception as e:
        print('Error escribiendo dataset')
        print(e)

#Bloque main de llamada al procedimiento
if __name__ == "__main__":
    IN_inicio = int(sys.argv[1])
    IN_limite = int(sys.argv[2])
    IN_iconoAFichero = sys.argv[3].lower() == 'true'
    
    rastreo(IN_inicio, IN_limite, IN_iconoAFichero)