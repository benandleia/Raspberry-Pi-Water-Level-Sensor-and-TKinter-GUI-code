# -*- coding: utf-8 -*-

import tkinter as tk
import time
import RPi.GPIO as GPIO
from w1thermsensor import W1ThermSensor, core
import pandas
import urllib
import os
import http.client
from statistics import mode, StatisticsError

#Main Window class instantiation

class MainWindow(tk.Frame):
    def __init__(self, parent):
        self.parent = parent
        self.parent.protocol("WM_DELETE_WINDOW", self.QuitFunc)
        tk.Frame.__init__(self, parent)
        self.font_size = 36
        
        #Labels here
        self.WaterLevelLabel = tk.Label(self, text = "Water Volume (gal):")
        self.WaterLevelLabel.grid(row=0, column=0, pady= 25, padx =5, sticky = "NW")
        self.WaterLevelLabel.configure(font = ("Courier", self.font_size))
        
        self.CabinTempLabel = tk.Label(self, text = "Cabin Temp (C):")
        self.CabinTempLabel.grid(row=1, column=0, pady = 10, padx =5, sticky = "NW")
        self.CabinTempLabel.configure(font = ("Courier", self.font_size))

        self.BoatShedTempLabel = tk.Label(self, text = "Boatshed Temp (C):")
        self.BoatShedTempLabel.grid(row=2, column=0, pady = 10, padx =5, sticky = "NW")
        self.BoatShedTempLabel.configure(font = ("Courier", self.font_size))
        
        self.OutsideTempLabel = tk.Label(self, text = "Outside Temp (C):")
        self.OutsideTempLabel.grid(row=3, column=0, pady = 10, padx =5, sticky = "NW")
        self.OutsideTempLabel.configure(font = ("Courier", self.font_size))
        
        #Tk StringVars
        self.CabinTemp = tk.StringVar()
        self.BoatShedTemp = tk.StringVar()
        self.OutsideTemp = tk.StringVar()
        
        #Entry widgets
        self.WaterLevelEntry = tk.Entry(self, width = 4)
        self.WaterLevelEntry.grid(row=0, column =1, pady=25, padx=5, sticky ="NW")
        self.WaterLevelEntry.configure(font = ("Courier", self.font_size))
        
        self.CabinTempEntry = tk.Entry(self, width = 4)
        self.CabinTempEntry.grid(row=1, column =1, pady=10, padx=5, sticky = "NW")
        self.CabinTempEntry.configure(font = ("Courier", self.font_size))

        self.BoatShedTempEntry = tk.Entry(self, width = 4)
        self.BoatShedTempEntry.grid(row=2, column =1, pady=10, padx=5, sticky = "NW")
        self.BoatShedTempEntry.configure(font = ("Courier", self.font_size))
        
        self.OutsideTempEntry = tk.Entry(self, width = 4)
        self.OutsideTempEntry.grid(row=3, column =1, pady=10, padx=5, sticky = "NW")
        self.OutsideTempEntry.configure(font = ("Courier", self.font_size))
        
        # Use BCM GPIO references
        # instead of physical pin numbers
        GPIO.setmode(GPIO.BCM)
        
        # Define GPIO to use on Pi
        self.GPIO_TRIGGER = 23
        self.GPIO_ECHO    = 16
        
        
        # Set pins as output and input
        GPIO.setup(self.GPIO_TRIGGER,GPIO.OUT)  # Trigger
        GPIO.setup(self.GPIO_ECHO,GPIO.IN)      # Echo
      
        
        #Define sensor IDs for ds18b20 temp sensors
        try:
            self.boatshed_temp_sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "3c01a81697f1")
            self.cabin_temp_sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "3c01a816adf1")
            self.outside_temp_sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, "0301a279a203")
        except core.NoSensorFoundError:
            print("Error, could not connect to temp sensor!")
            
        #ThingSpeak Key
        self.key = "23SM5XQ3WHGJTXN9"
        
        #Get the current time to initialize path
        self.time_path = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    
        #File path
        self.filepath = ("/home/pi/hornby_data/hornby_data_" + self.time_path)
        
        #Run the update functions, and post to ThingSpeak
        self.Update_temps()
        self.Update_water()
        self.RecordData()
        self.PostMessage()
        
        
        
    def DistMeasure(self):
        try:
            self.ss_temperature = self.outside_temp_sensor.get_temperature()
        except:
            #Give a default temp of 15C, in case temp sensor cannot be read.
            self.ss_temperature = 15
        self.speedSound = 34800 + (0.606 * self.ss_temperature)
        # This function measures a distance
        GPIO.output(self.GPIO_TRIGGER, True)
        # Wait 10us
        time.sleep(0.00001)
        GPIO.output(self.GPIO_TRIGGER, False)
        start = time.time()
      
        while GPIO.input(self.GPIO_ECHO)==0:
         start = time.time()
    
        while GPIO.input(self.GPIO_ECHO)==1:
         stop = time.time()
    
        elapsed = stop-start
        self.distance = (elapsed * self.speedSound)/2        
        return self.distance
    
    def measure_average(self):
        # This function takes 3 measurements and
        # returns the average.
      try:
          self.dist_buffer = [None]*15
          for i in range(len(self.dist_buffer)):
              self.dist_buffer[i] = round(self.DistMeasure(),1)
              time.sleep(0.1)
          self.dist_mode = mode(self.dist_buffer)    
          self.dist_buffer = [None]*15
      except StatisticsError:
          self.dist_mode = -200
          self.dist_buffer = [None]*15
      return self.dist_mode   

        
    #Update temp values every 3 seconds
    def Update_temps(self):
        try:
            self.cabin_temp = self.cabin_temp_sensor.get_temperature()
            self.outside_temp = self.outside_temp_sensor.get_temperature()
            self.boatshed_temp = self.boatshed_temp_sensor.get_temperature()
        except:
            self.cabin_temp = "NC"
            self.outside_temp = "NC"
            self.boatshed_temp = "NC"
        self.CabinTempEntry.delete(0, tk.END)    
        self.CabinTempEntry.insert(0, f'{self.cabin_temp}')
        self.BoatShedTempEntry.delete(0, tk.END)
        self.BoatShedTempEntry.insert(0, f'{self.boatshed_temp}')
        self.OutsideTempEntry.delete(0, tk.END)
        self.OutsideTempEntry.insert(0, f'{self.outside_temp}')
        self.after(10000, self.Update_temps)
        
    #Update water level values every 10 seconds
    def Update_water(self):
        self.measure_average()
        self.water_height = 153 - self.dist_mode
        self.gallons = self.water_height * 20.47
        self.gallons = round(self.gallons)
        self.WaterLevelEntry.delete(0, tk.END)
        if(self.gallons == 7226):
            self.WaterLevelEntry.insert(0,"WAIT")
        else:
            self.WaterLevelEntry.insert(0, f'{self.gallons}')
        self.after(60000, self.Update_water)
    
    def RecordData(self):
    #Assemble sensor readings into a list object
        self.data = {"Date": [time.strftime("%Y-%m-%d", time.localtime())], "Time": [time.strftime("%H:%M:%S", time.localtime())],
            "Tank_Water_Volume": [self.gallons], "Cabin_Temp": [self.cabin_temp], "Boatshed_temp": [self.boatshed_temp],"Outside_temp": [self.outside_temp]}
   
        #Create a pandas DataFrame object
        self.df = pandas.DataFrame (self.data, columns = ["Date","Time","Tank_Water_Volume","Cabin_temp","Boatshed_temp","Outside_temp"])
    
        #Write the DataFrame object to a .CSV file, located on the Raspberry Pi Desktop
        self.df.to_csv(self.filepath, mode = 'a', header = False, index = False)
        self.after(300000, self.RecordData)
        
    def PostMessage(self):
        self.params = urllib.parse.urlencode({'field1' : self.gallons, 'field2' : self.cabin_temp, 'field3' : self.outside_temp, 'field4' : self.boatshed_temp,'key':self.key})
 
        #Configure header / connection address
        self.headers = {"Content-typZZe": "application/x-www-form-urlencoded","Accept": "text/plain"}
        self.conn = http.client.HTTPConnection("api.thingspeak.com:80")
  
        #Try to connect to ThingSpeak and send Data
        try:
            self.conn.request("POST", "/update", self.params, self.headers)
            response = self.conn.getresponse()
            print( response.status, response.reason)
            data = response.read()
            self.conn.close()
      
        #Catch the exception if the connection fails
        except:
            print( "connection failed")
        self.after(300000, self.PostMessage)
    
    #Function to edit default program exiting behaviour
    def QuitFunc(self):
        GPIO.cleanup()
        os.system("sudo modprobe -r w1-therm w1-gpio")
        self.parent.destroy()
    
###################################################################################################################
#                                        CALL MAINLOOP
                                        
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Hornby Cabin Sensors V.1")
    App = MainWindow(root).grid(row=0, column=0)
    root.mainloop()


