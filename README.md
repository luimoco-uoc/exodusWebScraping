# **exodusWebScraping**

### Dataset del tratamiento de la privacidad del usuario por parte de las aplicaciones móviles

<div align="center"><img src="https://i.ibb.co/k6gb85C/exodusWS.jpg" alt="exodusWS" border="0" width = "1024" height = "320"></div>

## Descripción
Con motivos académicos para el Máster en Ciencia de Datos de la UOC, se realiza el proyecto de extracción de información mediante técnicas de Web Scraping sobre el sitio web <a href = "https://exodus-privacy.eu.org/en/">Exodus-Privacy</a> dedicado a analizar aspectos de seguridad y privacidad en aplicaciones Android. El dataset *Tratamiento de la privacidad del usuario por parte de aplicaciones móviles*, proporciona información de rastreadores que se han incluido en la aplicación y los permisos del dispositivo que ha de aceptar el usuario en el momento de su instalación. Adicionalmente proporciona más características de la aplicación interesantes para el tratamiento analítico de aplicaciones móviles.

## Código fuente y recursos
* **src/exodusWS.py**: Script de python con el programa principal y métodos utilizados para el rastreo.
* **data/exodus.json**: Dataset obtenido a fecha 07/11/2020.
* **rsc/M.2851_PRA1_luimoco.pdf**: Informe de respuesta a los objetivos demandados en la práctica.
* **rsc/Consideraciones Teóricas User-Agents.pdf**: Documento de análisis de requisitos de un buen user-agent recopilados del libro de texto.
* **rsc/Análisis Exodus User-Agent.pdf**: Documento de análisis del rastreador.
* **rsc/Diseño Exodus User-Agent.pdf**: Documento de diseño del rastreador.

## Instalación y ejecución exodusWS.py
### Dependencias:
~~~
import time
from bs4 import BeautifulSoup
import regex as re
import requests
import json
from datetime import datetime
from skimage import io, transform
import numpy as np
~~~

### Ejecución:
~~~
python exodusWS.py --inicio @inicio --limite @limite
~~~
Donde:
* **@inicio**: Entero de 1 a n que indica al rastreador en qué página de informe de aplicación comenzar https://reports.exodus-privacy.eu.org/es/reports/1/
* **@limite**: Entero positivo que indica al rastreador cuántas páginas de informes de aplicaciones tratar.

### Salida:
La ejecución del proceso obtiene como resultado la creacion o modificación y creación de tres ficheros:
* **exodus.json**: Fichero acumulativo donde se almacena el dataset en formato json. Si es la primera ejecución se crea. Si ya existe, el proceso lee las aplicaciones rastreadas y solamente vuelve a rastrear las nuevas dentro del rango fijado en los parámetros del procedimiento.
* **exodus_inicio_fin.json**: Se crea el fichero con el dataset resultado de la ejecución concreta.
* **incidencias_inicio_fin.json**: Se recoge el log de incidencias acontecidas durante el proceso de rastreo para afinar el script.

### Configuración:
Los siguientes parámetros del script son constantes de configuración que se pueden modificar en el propio script:
* **MAX_REINTENTOS** = 3: Número de reintentos sobre la misma página en errores no fatales antes de pasar a la siguiente aplicación.
* **TOLERANCIA_ERRORES** = 3: Número de atributos máximo que podrán quedar sin informar *na* por errores o ausencia de la información en el rastreo de la página de informe de la aplicación. Si se supera, no se adjunta el elemento al dataset.
* **MOTIVOS** (en función gestionarTiempos): Se trata de un diccionario de constantes con el número de segundos a esperar según ciertas situaciones que pueden producirse:
    * **'ESPERA_ESTANDAR'**:3 > Segundos de cortesía entre peticiones Request a páginas para no satuar el servidor.
    * **'ESPERA_ERROR_CONEXION'**:3600 > Segundos a esperar si se detecta un error de conexión en la petición Request de la página.
    * **'ESPERA_TIMEOUT'**:300 > Segundos a esperar si se detecta un error de timeot en la petición Request de la página.
    * **'ESPERA_ERROR_SERVIDOR'**:3600 > Segundos a esperar si el servidor devuelve un código html de error de servidor 500~600.
    * **'ESPERA_ERROR_CLIENTE'**: 5 > Segundos a esperar si el servidor devuelve un código html de error en el cliente 400~500.
    * **'ESPERA_CORRECTA_INCIDENCIAS'**:10 > Segundos de espera si el serivdor devuelve un código html de servicio correcto con incidencias 201~300.
    
## Estructura del dataset
El dataset está estructurado en un fichero de formato Json con la siguiente estructura de atributos de sus elementos:  
{  
  'Id' : id, *Número entero identificador de la aplicación*  
  'Name' : “nombre”, *Texto con el nombre de la aplicación*  
  'Tracker_count' : cuenta_rastreadores, *Numérico con el número de rastreadores incrustados en la app*  
  'Permissions_count' : cuenta_permisos, *Numérico con el número de permisos solicitados en la app*  
  'Version' : 'versión', *Texto con el versionado de la aplicación*  
  'Downloads' : 'descargas', *Texto con el número aproximado de descargas*  
  'Analysis_date': 'analysis_date', *Texto con la fecha de realización del informe*  
  'Trackers' : [{'nombre_rastreador' : ['propósito']}] *Lista de nombres de rastreadores encontrados que encadena otra lista de los propósitos que tienen*  
  'Permissions' : ['permisos'] *Lista de permisos que requiere la app del terminal*  
  'Permissions_warning_count' : cuenta_permisos_críticos *Número de permisos considerados críticos para salvaguardar la privacidad que requiere la app*  
  'Country' : 'país' *Código textual del país del desarrollador de la app*  
  'Developer' : 'desarrollador' *Texto con el nombre del desarrollador de la app*  
  'Icon' : “[[RGBA]]” *Codificación del icono en 32x32 componentes con la información RGBA en bytes del pixel correspondiente*  
}
