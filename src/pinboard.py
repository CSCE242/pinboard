'''
Pinboard : a CSCE 242 project.
Created on May 16, 2012
www.csce242.com

@author: Jose M Vidal <jmvidal@gmail.com>

Homework 4
'''
import webapp2
import jinja2
import os
import logging #for debugging.
from google.appengine.api import users
from google.appengine.ext import db

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/templates"))

class Pin(db.Model):
    imgUrl = db.StringProperty(required=True)
    caption = db.StringProperty(indexed=False)
    date = db.DateTimeProperty(auto_now_add=True)
    owner = db.UserProperty(required=True)
    private = db.BooleanProperty(default=False)
    boards = db.ListProperty(db.Key)

    def id(self):
        return self.key().id()

    @staticmethod #just like a Java static method
    def getPin(id): 
        """Returns the pin with the given id (a String), or None if there is no such id."""
        key = db.Key.from_path('Pin', long(id))
        thePin = db.get(key)
        return thePin
    
    
class Board(db.Model):
    title = db.StringProperty(required=True)
    owner = db.UserProperty(required=True)
    private = db.BooleanProperty(default=False)
    pins = db.ListProperty(db.Key) #references to the pins in this pinboard
    
    def id(self):
        return self.key().id()

    @staticmethod    
    def getBoard(id):
        """Returns the board with the given id (a String), or None if there is no such id."""
        key = db.Key.from_path('Board', long(id))
        theBoard = db.get(key)
        return theBoard
    
    
class MyHandler(webapp2.RequestHandler):
    "Setup self.user and self.templateValues values."
    def setupUser(self):
        self.user = users.get_current_user()
        self.templateValues = {}
        if self.user:
            self.templateValues['logout'] = users.create_logout_url('/')
            self.templateValues['username'] = self.user.nickname()
        else:
            self.templateValues['login'] = users.create_login_url('/')
            
    def render(self, file):
        "Render the given file"
        template = jinja_environment.get_template(file)
        self.response.out.write(template.render(self.templateValues))
        

class MainPageHandler(MyHandler):
    def get(self): #/ Ask user to login or show him links
        self.setupUser()
        if self.user:
            self.templateValues['user'] = self.user
        self.templateValues['title'] = 'Pinboard'
        self.render('main.html')
        
        
class PinHandler(MyHandler):
    def get(self,id):
        self.setupUser()    
        logging.info('id is=%s' % id)
        if id == '': # GET /pin returns the list of pins for this user
            query = Pin.all().filter('owner =', self.user) #Remember: "owner=" won't work!!!
            self.templateValues['pins'] = query
            self.templateValues['title'] = 'Your Pins'
            self.render('pinlist.html')
            return
        thePin = Pin.getPin(id)
        if thePin == None:
            self.redirect('/') 
            return
        if (not thePin.private) or self.user == thePin.owner:
            self.templateValues['pin'] = thePin
            self.templateValues['id'] = id
            self.templateValues['title'] = id
            self.render('pin.html')
        else:
            self.redirect('/')
    
    def post(self,id):
        """If /pin/ then create a new one, if /pin/123 then update it,
        if /pin/123?cmd=delete then delete it."""
        self.setupUser()
        imgUrl = self.request.get('imgUrl')
        caption = self.request.get('caption')
        command = self.request.get('cmd')
        private = self.request.get('private')
        private = True if (private == "on") else False
        owner = self.user
        if id == '': #new pin, create it
            thePin = Pin(imgUrl = imgUrl, caption = caption, owner = owner, private = private)
            thePin.put()
        else:
            thePin = Pin.getPin(id)
            if thePin == None:
                self.redirect('/')  
                return            
            if thePin.owner != self.user: #not his pin, kick him out.
                self.redirect('/')
                return
            if command == 'delete': #delete the pin
                thePin.delete()
                self.redirect('/pin/')            
                return
            else: #existing pin, update it 
                thePin.imgUrl = imgUrl
                thePin.caption = caption
                thePin.private = private
                thePin.put()
        key = thePin.key()
        newUrl = '/pin/%s' % key.id()
        logging.info('Going to ' + newUrl)
        self.redirect(newUrl)

class BoardHandler(MyHandler):
    def get(self,id): #/board/
        self.setupUser()
        if id == '': # GET /board returns the list of pins for this user
            query = Board.all().filter('owner =', self.user) #Remember: "owner=" won't work!!!
            self.templateValues['boards'] = query
            self.templateValues['title'] = 'Your Boards'
            self.render('boardlist.html')
            return
        theBoard = Board.getBoard(id)
        if theBoard == None: return
        if (not theBoard.private) or self.user == theBoard.owner:
            self.templateValues['board'] = theBoard
            self.templateValues['id'] = id
            self.templateValues['title'] = id
            myPins = Pin.all().filter('owner =', self.user)            
            self.templateValues['myPins'] = myPins
            boardPins = []
            for p in theBoard.pins:
                boardPins.append(Pin.get(p))
            self.templateValues['boardPins']= boardPins
            self.render('board.html')
        else:
            self.redirect('/')
    
    def post(self,id):
        self.setupUser()
        title = self.request.get('title')
        command = self.request.get('cmd')
        private = self.request.get('private')
        private = True if (private == "on") else False
        owner = self.user
        if id == '': #new board, create it
            theBoard = Board(title = title, owner = owner, private = private)
            theBoard.put()
        else:
            theBoard = Board.getBoard(id)
            if theBoard == None:
                self.redirect('/')  
                return            
            if theBoard.owner != self.user: #not his pin, kick him out.
                self.redirect('/')
                return
            if command == 'delete': #delete the pin
                theBoard.delete()
                self.redirect('/board/')            
                return
            else: 
                pinToAdd = self.request.get('addPin')
                if pinToAdd != None and pinToAdd != 'none': 
                    thePin = Pin.getPin(pinToAdd) #only add pin if it exists and its mine and its not already in.
                    if thePin != None and thePin.owner == self.user and not (thePin.key() in theBoard.pins):
                        theBoard.pins.append(thePin.key())
                pinToDelete = self.request.get('deletePin')
                if pinToDelete != None and pinToDelete != 'none': #delete a pin 
                    thePin = Pin.getPin(pinToDelete) 
                    if thePin != None and thePin.owner == self.user and (thePin.key() in theBoard.pins):
                        theBoard.pins.remove(thePin.key())
                theBoard.title = title
                theBoard.private = private
                theBoard.put()
        key = theBoard.key()
        newUrl = '/board/%s' % key.id()
        self.redirect(newUrl)


app = webapp2.WSGIApplication([('/pin/(.*)', PinHandler), ('/pin()', PinHandler),
                               ('/board/(.*)', BoardHandler), ('/board()', BoardHandler), 
                               ('/', MainPageHandler)],
                              debug=True)
