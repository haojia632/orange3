# -*- coding: utf-8 -*-
"""
Created on Thu Jan 24 21:11:40 2019

@author: Administrator
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from Orange.data.io import FileFormat
import Orange
import numpy as np
from sklearn import manifold,decomposition
from copy import deepcopy
import matplotlib as mpl
import matplotlib.cm as cm
import matplotlib.gridspec as gridspec #整理

class Normal:
    '''
    使用情况：
    用于一组数据：(num,dim)形成的数组array,对其进行归一化；
    此外还用于单个数据：(dim,) 或(num1,dim),对其进行反归一化得到真实数据
    '''
    def __init__(self,X,Xrange=None):
        self.X = np.array(X)
        ## Xrange是一个是二维数组dim X 2:【【Lower1,Upper1】,【Lower2,Upper2】...】
        if Xrange is None:
            self.Xrange = self.get_range(self.X)
        else:
            self.Xrange = np.array(Xrange)
        self.interval = np.ptp(self.Xrange,axis=1)#获取区间大小
        
    def get_range(self,X):
        X = np.array(X)
        num,dim = X.shape
        min_max_range = [[X[:,i].min(),X[:,i].max()] for i in range(dim)]
        return np.array(min_max_range)
        
    def Normalization(self,test_X):#将一条或多条数据正则化
        X = np.array(test_X)
        if isinstance(X[0],float) or isinstance(X[0],int):   
            X_new = [(X[i]-self.Xrange[i,0])/self.interval[i] for i in range(len(X))]
            X_new = np.array(X_new).T
        else:       
            row,col = X.shape
            X_new = [ (X[:,i]-self.Xrange[i,0])/self.interval[i] for i in range(col)]
            X_new = np.array(X_new).T
        return X_new

    def InverseNormalize(self,test_X):#将正则化后的数据变为原来的数值
        X = np.array(test_X)
        if isinstance(X[0],float) or isinstance(X[0],int):   
            X_new =[(X[i]+self.Xrange[i,0])*(self.Xrange[i,1]-self.Xrange[i,0]) for i in range(len(X))]
            X_new = np.array(X_new).T   
        else:
            row,col = X.shape
            X_new =[(X[:,i]+self.Xrange[i,0])*(self.Xrange[i,1]-self.Xrange[i,0]) for i in range(col)]
            X_new = np.array(X_new).T  
        return X_new

class DraggablePoint:
#    lock = None
    def __init__(self,fig,ax1,ax2,ax3,ax4,line1,line2,scalarMap,pca,Normal,model):
        global doc
        global Bottle
        global box
        self.line1 = line1
        self.line2 = line2
        self.lines3 = []
        self.lines4 = []
        self.fig=fig
        self.model=model
        self.pca = pca
        self.scalarMap= scalarMap
        self.Normal = Normal
        if len(ax3) == 1:
            raise ValueError('Length of input axes need to be greater than 1,now is 1')
        self.axs3 = ax3
        self.axs4 = ax4
        self.press = None
        self.lastind = 0

        self.dim = len(ax3)
        X = np.array([i for i in range(self.dim)])
        Y = np.zeros(self.dim)
        self.selected1, = ax1.plot(X,Y,
                                  'o-',ms=10,alpha=0.5,
                                  color='gray',visible=False) 
        self.selected2, = ax2.plot(0,0,
                                  'o',ms=10,alpha=0.5,
                                  color='gray',visible=False)
        self.selected3 = []
        for i,ax in enumerate(self.axs3):
            line, = ax.plot(0,0,'o',ms=10,alpha=0.5,
                            color='red',visible=False)
            self.selected3.append(line)
            
        self.selected4 = []
        for i,ax4 in enumerate(self.axs4):
            line4, = ax4.plot(0,0,'o',ms=5,alpha=0.2,
                            color='gray',visible=False)
            self.selected4.append(line4)
    
    def connect(self): 
        self.line1.figure.canvas.mpl_connect(
                'pick_event',self.on_press)
        self.line1.figure.canvas.mpl_connect(
                'button_release_event',self.on_release)
        self.line1.figure.canvas.mpl_connect(
                'motion_notify_event',self.on_motion)    
        
    def on_press(self,event):  
        if event.artist not in [self.line1 ,self.line2]:
            return
        if event.artist == self.line1:
            x0 = self.line1.get_xdata()
            y0 = self.line1.get_ydata()
            x = event.mouseevent.xdata
            y = event.mouseevent.ydata
            '''确定event发生，看见self.line1中距离最近的点'''
            distance = np.hypot(x-x0,y-y0)
            indmin = distance.argmin()
            self.lastind = indmin 
            self.press = x0,y0,x,y     

        else:     
            x0 = self.line2.get_xdata()
            y0 = self.line2.get_ydata()
            x = event.mouseevent.xdata
            y = event.mouseevent.ydata      
            '''确定event发生，看见self.line2中距离最近的点'''
            distance = np.hypot(x-x0,y-y0)
            indmin = distance.argmin()
            self.lastind = indmin
            self.press = x0,y0,x,y        

    def on_motion(self,event):
        if self.press is None:
            return
        if event.inaxes not in [self.line1.axes,self.line2.axes]:
            return
        if event.inaxes == self.line1.axes:
           
            '''
            实现ax1到ax2的链接
            '''   
            x0,y0,mx,my = self.press# y0表示on_press选取上的line1的坐标 
            y0[self.lastind] = event.ydata #上表示改变其中选取的那个点的坐标，其他坐标不变
            print (x0,y0,mx,my)
            self.line1.set_ydata(y0) #改变line1中个点的y坐标（实际只变动了1维）
            iteration_y = np.array(self.line1.get_ydata()).reshape(1,-1)
            Data_new = self.pca.transform(iteration_y) #根据line1的坐标确定line2的坐标
            self.line2.set_xdata(Data_new[:,0].reshape(-1,1))
            self.line2.set_ydata(Data_new[:,1].reshape(-1,1))
            print ('123',self.Normal.InverseNormalize(y0))
            
            l=len(self.Normal.InverseNormalize(y0))
            m=["0"]*l
            name=m+self.Normal.InverseNormalize(y0)         
            Mytable = FileFormat.data_table(name)
            y1 = self.model(Mytable,0)#确定选中线的颜色
            print('y1',y1)
     
            self.line1.set_color(self.scalarMap.to_rgba(y1))
            self.line2.set_color(self.scalarMap.to_rgba(y1))
           
        self.fig.canvas.draw() 

    def on_release(self,event):
        for i,line in enumerate(self.lines3):
            line.set_visible(False) 
        for i,ax in enumerate(self.axs3):
            self.selected3[i].set_visible(False)
        self.press = None
        self.line1.figure.canvas.draw()
    
class CanvasDraw:
    def __init__(self,x_label,xrange,fig,model):
        self.X_label =x_label
        self.Xrange=xrange
        self.fig=fig
        self.model=model

    def flabelXH(x_label,xrange,fig,model):
        X_label =x_label
        Xrange=xrange
        Xborder = np.array(Xrange)
         #设置生成数据点的数量
        data_num =100
        X = [rangei[0]+np.random.random(data_num)*(rangei[1]-rangei[0]) for rangei in Xrange]
        X = np.array(X).T
        X = X.astype(np.float64)

        # X = X.tolist()
        # print('1234567',X)
        # l = len(X[0])
        # m = ["a","b","c"]
        # # for i in range(l):
        # #     m.append('a')
        # # new_X = []
        # for k in range(len(X)):
        #     for q in range(len(X[0])+1):
        #         X[k][q] = str(X[k][q])
        # m = [m]
        # print('m',m)
        # name = m + X
        # print('name', name)
        # Mytable = FileFormat.data_table(name)

        length = Orange.data.ContinuousVariable("上")
        width = Orange.data.ContinuousVariable("宽")
        height = Orange.data.ContinuousVariable("高")
        volumn = Orange.data.ContinuousVariable("体积")

        domain = Orange.data.Domain([length, width, height], volumn)

        Y = np.random.random(len(X))
        Y = Y.astype(np.float64)

        Mytable = Orange.data.Table(domain, X, Y)

        print('2', Mytable)
        f = model(Mytable,0)
        print('f', f)
        ## 归一化处理输入X，并且幅值为Y_data
        NormalObject = Normal(X,Xrange)
        Y_data = NormalObject.Normalization(X)
        num,dim = Y_data.shape
        X_data  = np.array([i for i in range(dim)])
        
        ## PCA处理数据:对归一化数据：Y_data进行操作
        pcaObj = decomposition.PCA(n_components=2).fit(Y_data)
        Y_low = pcaObj.transform(Y_data)
    
        '''设置Axes的布局'''
    #    fig = plt.figure(figsize=(15,5))
        dim=3
        gs = gridspec.GridSpec(2, dim+1,
                               width_ratios=[2]+[1]*(dim),
                               height_ratios=[2, 2])
        AxesNum = (dim+1)*2
        axes = []
        for i in range(AxesNum):
            ax = plt.subplot(gs[i])
            axes.append(ax)
        plt.tight_layout()
        ax1 = axes[0]  ##水平坐标系图
        ax2 = axes[dim+1] ##PCA降维图
        ax3 = axes[1:dim+1] ## X-f1关系图
        ax4 = axes[dim+2:AxesNum] 
        
        vmin, vmax = f.min(),f.max()
        norm = mpl.colors.Normalize(vmin=vmin,vmax=vmax)
        jet = plt.get_cmap('jet')
        scalarMap = cm.ScalarMappable(norm=norm,cmap=jet)
        scalarMap.set_array([])
                
        '''
        平行坐标系，pca降维图
        '''
        #绘制平行坐标系，pca降维图静态背景图
        lines1 = []
        lines2= []
        for i in range(num):
            colorVal = scalarMap.to_rgba(f[i])
            line, = ax1.plot(X_data,Y_data[i,:],color = colorVal,linewidth=0.5,marker='.')
            line2, = ax2.plot(Y_low[i,0],Y_low[i,1],color = colorVal,alpha=0.5,marker='.')
            lines1.append(line)
            lines2.append(line2)        
             
        # 设置能够移动的线和点
        colorVal = scalarMap.to_rgba(f[0])
        lines1,=ax1.plot(X_data,Y_data[0,:],color = colorVal,linestyle='--',linewidth=2,
                             marker='o',mec='Black',mfc='black',markersize=10,picker=5)
        lines2,=ax2.plot(Y_low[0,0],Y_low[0,1],
                              color = colorVal,marker='o',mec='Black',markersize=6,picker=5)
        
        '''
        坐标轴设置
        '''
        #加ax1标题
        ax1.set_title('High dimensionality',fontsize=15)
        
        #ax1上x轴的label设置
        ax1.set_xticks(X_data)
        ax1.set_xticklabels(X_label,fontsize=15)
        
        # ax1的y轴设置为不可见
        ax1.get_yaxis().set_visible(False)
        
        #给ax1加竖线作为纵轴
        ax1.axvline(x='x1', color='#000000', linewidth=1);
        ax1.axvline(x='x2', color='#000000', linewidth=1);
        ax1.axvline(x='x3', color='#000000', linewidth=1);
        
        #添加ax1上纵轴的最大值和最小值
        for i in range(1,4):
            si1=int(Xborder[(i-1)].min())
            si2=int(Xborder[(i-1)].max())
            ax1.text(i-1.15,-0.05,si1,fontsize=13)
            ax1.text(i-1.15,1,si2,fontsize=13)
        
        #ax1,ax2的colorbar设置
        fig.colorbar(scalarMap,ticks = [vmin, vmax],ax=ax1)
        fig.colorbar(scalarMap,ticks = [vmin, vmax],ax=ax2)
        
        ##设置ax2的坐标label和title
        ax2.set_title('Low dimensionality',fontsize=15)
        ax2.set_xlabel('Dim1')
        ax2.set_ylabel('Dim2')
        
        ##设置ax3，ax4的坐标label和title
        for i,ax in enumerate(ax3):
            ax.set_xlabel(X_label[i],fontsize=13)
            ax.set_ylabel('y1',fontsize=13)
            ax.set_title('%s-%s relation'%(X_label[i],'y1'),fontsize=15)
            
        for i,ax in enumerate(ax4):
            ax.set_xlabel(X_label[i],fontsize=13)
            ax.set_ylabel('y1',fontsize=13)
            ax.set_title('%s-%s distribution'%(X_label[i],'y1'),fontsize=15)   
        
        plt.tight_layout()
        return [fig,ax1,ax2,ax3,ax4,lines1,lines2,scalarMap,pcaObj,NormalObject]
