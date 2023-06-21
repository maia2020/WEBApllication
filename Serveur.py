# TD3-s7.py (corrigé §5.1)

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs, unquote
import json

import matplotlib

import matplotlib.pyplot as plt
import datetime as dt
import matplotlib.dates as pltd
from datetime import datetime

import sqlite3

#
# Définition du nouveau handler
#
class RequestHandler(http.server.SimpleHTTPRequestHandler):

  # sous-répertoire racine des documents statiques
  static_dir = '/client'

  #
  # On surcharge la méthode qui traite les requêtes GET
  #
  def do_GET(self):

    # On récupère les étapes du chemin d'accès
    self.init_params()

    # le chemin d'accès commence par /time
    if self.path_info[0] == 'time':
      self.send_time()
   
     # le chemin d'accès commence par /regions
    elif self.path_info[0] == 'regions':
      self.send_regions()
      
    # le chemin d'accès commence par /ponctualite
    elif self.path_info[0] == 'regularite':
      self.send_concentration()

    elif self.path_info[0] == 'comparasion':
      self.send_comparasion()
      
    # ou pas...
    else:
      self.send_static()

  #
  # On surcharge la méthode qui traite les requêtes HEAD
  #
  def do_HEAD(self):
    self.send_static()

  #
  # On envoie le document statique demandé
  #
  def send_static(self):

    # on modifie le chemin d'accès en insérant un répertoire préfixe
    self.path = self.static_dir + self.path

    # on appelle la méthode parent (do_GET ou do_HEAD)
    # à partir du verbe HTTP (GET ou HEAD)
    if (self.command=='HEAD'):
        http.server.SimpleHTTPRequestHandler.do_HEAD(self)
    else:
        http.server.SimpleHTTPRequestHandler.do_GET(self)
  
  #     
  # on analyse la requête pour initialiser nos paramètres
  #
  def init_params(self):
    # analyse de l'adresse
    info = urlparse(self.path)
    self.path_info = [unquote(v) for v in info.path.split('/')[1:]]
    self.query_string = info.query
    self.params = parse_qs(info.query)

    # récupération du corps
    length = self.headers.get('Content-Length')
    ctype = self.headers.get('Content-Type')
    if length:
      self.body = str(self.rfile.read(int(length)),'utf-8')
      if ctype == 'application/x-www-form-urlencoded' : 
        self.params = parse_qs(self.body)
      elif ctype == 'application/json' :
        self.params = json.loads(self.body)
    else:
      self.body = ''
   
    # traces
    print('info_path =',self.path_info)
    print('body =',length,ctype,self.body)
    print('params =', self.params)
    
  #
  # On envoie un document avec l'heure
  #
  def send_time(self):
    
    # on récupère l'heure
    time = self.date_time_string()

    # on génère un document au format html
    body = '<!doctype html>' + \
           '<meta charset="utf-8">' + \
           '<title>l\'heure</title>' + \
           '<div>Voici l\'heure du serveur :</div>' + \
           '<pre>{}</pre>'.format(time)

    # pour prévenir qu'il s'agit d'une ressource au format html
    headers = [('Content-Type','text/html;charset=utf-8')]

    # on envoie
    self.send(body,headers)

  #
  # On génère et on renvoie la liste des régions et leur coordonnées (version TD3, §5.1)
  #
  def send_regions(self):

    conn = sqlite3.connect('polluants.sqlite')
    c = conn.cursor()
    
    c.execute("SELECT * FROM 'regions'")
    r = c.fetchall()
    
    headers = [('Content-Type','application/json')];
    body = json.dumps([{'nom':n, 'lat':lat, 'lon': lon} for (n,lat,lon) in r])
    self.send(body,headers)

  #
  # On génère et on renvoie un graphique de ponctualite (cf. TD1)
  #
  def send_concentration(self):

    conn = sqlite3.connect('polluants.sqlite')
    c = conn.cursor()
    polluants = [row[0] for row in c.execute("SELECT DISTINCT Polluant FROM 'polluants'")]

    # si pas de paramètre => liste par défaut
    if len(self.path_info) <= 1 or self.path_info[1] == '' :
        # Definition des régions et des couleurs de tracé
        regions = [("Rhône Alpes","blue"), ("Auvergne","green"), ("Auvergne-Rhône-Alpes","cyan"), ('Bourgogne',"red"), 
                   ('Franche Comté','orange'), ('Bourgogne-Franche-Comté','olive') ]
        title = 'Concentration de polluants en %'
    else:
        # On teste que la région demandée existe bien
        c.execute("SELECT DISTINCT Région FROM 'polluants'")
        r = c.fetchall()

        # Rq: r est une liste de tuples
        if (self.path_info[1],) in r:
          regions = [(self.path_info[1],"blue")]
          title = 'Concentration des polluants en region {} (en %)'.format(self.path_info[1])

        # Région non trouvée -> erreur 404
        else:
            print ('Erreur nom')
            self.send_error(404)
            return None
    
    # configuration du tracé
    plt.figure(figsize=(16,6))
    plt.ylim(0,100)
    plt.grid(which='major', color='#888888', linestyle='-')
    plt.grid(which='minor',axis='x', color='#888888', linestyle=':')
    
    ax = plt.subplot(111)
    loc_major = pltd.YearLocator()
    loc_minor = pltd.MonthLocator()
    ax.xaxis.set_major_locator(loc_major)
    ax.xaxis.set_minor_locator(loc_minor)
    format_major = pltd.DateFormatter('%B %Y')
    ax.xaxis.set_major_formatter(format_major)
    ax.xaxis.set_tick_params(labelsize=10)
    
    # boucle sur les régions
    # boucle sur les régions
    for reg in (regions) :
        #Queremos recuperar apenas as linhas entre as datas indicadas

        c.execute("SELECT * FROM 'polluants' WHERE Région=? AND Date BETWEEN ? AND ? ORDER BY Date", (reg[0], self.path_info[2], self.path_info[3]))

        # c.execute("SELECT * FROM 'polluants' WHERE Région=? ORDER BY Date",reg[:1])  # ou (reg[0],)
        r = c.fetchall()
        # récupération de la concentration (3e colonne)
        for polluant in polluants:
          # Filtro adicional para selecionar apenas as linhas com o "Polluant" desejado
          filtered_r = [row for row in r if row[3] == polluant]
          # print(filtered_r)
          # Verificar se existem dados disponíveis para o "Polluant" selecionado
          if filtered_r:
              # Recuperação da concentração (3ª coluna) para o "Polluant" selecionado
              y = [float(a[2]) for a in filtered_r]
              # print(y)
              
              # Recuperação da data (1ª coluna) correspondente aos dados disponíveis'
              # for a in filtered_r:
              #   print(a[0])
              x_filtered = [pltd.date2num(dt.date(int(a[0][:4]), int(a[0][5:7]), int(a[0][8:]))) for a in filtered_r]
              # print(x_filtered)
              print('x_filtered =', type(x_filtered[0]))
              print('x_filtered =', x_filtered[:20])
              # Traçar a curva para o "Polluant" atual
              plt.plot(x_filtered[:100], y[:100], linewidth=1, linestyle='-', label=f"{reg[0]} - {polluant}")
        
        
        
    # légendes
    plt.legend(loc='upper right')
    plt.title('Concentration des Polluants (en %)',fontsize=10)
    plt.ylabel('% de Concentration')
    plt.xlabel('Date')

    # génération des courbes dans un fichier PNG
    fichier = 'courbes/concentration_'+self.path_info[1]+self.path_info[2]+self.path_info[3] +'.png'
    plt.savefig('client/{}'.format(fichier))

    #html = '<img src="/{}?{}" alt="ponctualite {}" width="100%">'.format(fichier,self.date_time_string(),self.path)
    body = json.dumps({
            'title': 'Concentration Polluants '+self.path_info[1]+self.path_info[2]+self.path_info[3], \
            'img': '/'+fichier \
             });
    # on envoie
    headers = [('Content-Type','application/json')];
    self.send(body,headers)

  def send_comparasion(self):
      
    conn = sqlite3.connect('polluants.sqlite')
    c = conn.cursor()
    poi1 = self.path_info[1]
    poi2 = self.path_info[2]
    polluant = self.path_info[3]

    # print(poi1)
    # print(poi2)
    # print(polluant)

    title = 'Comparaison des stations {} et {} pour le polluant {}'.format(self.path_info[1],self.path_info[2],self.path_info[3])

    # récupération des données
    c.execute("SELECT * FROM polluants WHERE Région = ? AND polluant = ? ORDER BY Date",(poi1,polluant))
    r = c.fetchall()
    c.execute("SELECT * FROM polluants WHERE Région = ? AND polluant = ? ORDER BY Date",(poi2,polluant))
    t = c.fetchall()
    # recupération de la date (1ère colonne) et transformation dans le format de pyplot
    print(len(t))

    x1 = [datetime.strptime(a[0],'%Y-%m-%d') for a in r ]
    xs = matplotlib.dates.date2num(x1)

    x2 = [datetime.strptime(a[0],'%Y-%m-%d') for a in t ]
    xs2 = matplotlib.dates.date2num(x2)
    print(len(xs2))
    
    hfmt = matplotlib.dates.DateFormatter('%Y-%m-%d')

    y1 = [float(a[2]) for a in r]

    y2= [float(a[2]) for a in t]
    print(len(y2))


    fig = plt.figure(figsize=(10,5))
    ax = fig.add_subplot(1,2,1)
    #Agora para a imagem com o segundo gráfico
    ax.xaxis.set_major_formatter(hfmt)
    plt.setp(ax.get_xticklabels(), rotation=15)
    ax.plot(xs,y1)
    plt.legend(loc='upper right')
    plt.title('Concentration des Polluants (en %)',fontsize=10)
    plt.ylabel('% de Concentration')
    plt.xlabel('Date')

    bx = fig.add_subplot(1,2,2)
    #Agora para a imagem com o segundo gráfico
    bx.xaxis.set_major_formatter(hfmt)
    plt.setp(bx.get_xticklabels(), rotation=15)
    bx.plot(xs2,y2)
    plt.legend(loc='upper right')
    plt.title('Concentration des Polluants (en %)',fontsize=10)
    plt.ylabel('% de Concentration')
    plt.xlabel('Date')



    #Pra salvar a imagem no diretório do servidor
    plt.savefig('client/comparasion_'+self.path_info[1]+self.path_info[2]+self.path_info[3] +'.png')
    fichier = 'comparasion_'+self.path_info[1]+self.path_info[2]+self.path_info[3] +'.png'
    


    # fichier = 'courbes/comparasion_'+self.path_info[1]+self.path_info[2]+self.path_info[3] +'.png'  
    # plt.savefig('client/{}'.format(fichier))

    #html = '<img src="/{}?{}" alt="ponctualite {}" width="100%">'.format(fichier,self.date_time_string(),self.path)
    body = json.dumps({
            'title': 'Comparasion de POIs '+self.path_info[1]+self.path_info[2]+self.path_info[3], \
            'img': '/'+fichier \
             });
    # on envoie
    headers = [('Content-Type','application/json')];
    self.send(body,headers)


            
    
  #
  # On envoie les entêtes et le corps fourni
  #
  def send(self,body,headers=[]):

    # on encode la chaine de caractères à envoyer
    encoded = bytes(body, 'UTF-8')

    # on envoie la ligne de statut
    self.send_response(200)

    # on envoie les lignes d'entête et la ligne vide
    [self.send_header(*t) for t in headers]
    self.send_header('Content-Length',int(len(encoded)))
    self.end_headers()

    # on envoie le corps de la réponse
    self.wfile.write(encoded)

 
#
# Instanciation et lancement du serveur
#
httpd = socketserver.TCPServer(("", 8080), RequestHandler)
httpd.serve_forever()

