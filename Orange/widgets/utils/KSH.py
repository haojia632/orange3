# -*- coding: utf-8 -*-
"""
Created on Thu Jan 24 21:09:57 2019

@author: Administrator
"""
from Orange.widgets.utils.KSHpkg import Normal,DraggablePoint,CanvasDraw
import matplotlib.pyplot as plt
class DTKSH:    
    def __init__(self,x_label,xrange,model):
        
        self.x_label=x_label
        self.xrange=xrange
        self.model=model
        x_label = self.x_label
        xrange = self.xrange
        fig=plt.figure(figsize=(15,5))
        fig,ax1,ax2,ax3,ax4,lines1,lines2,scalarMap,pcaObj,NormalObject=CanvasDraw.flabelXH(x_label,xrange,fig,self.model)        
        draggleLine = DraggablePoint(fig,ax1,ax2,ax3,ax4,lines1,lines2,scalarMap,pcaObj,NormalObject,self.model)
        draggleLine.connect()
        plt.show()