#
# gbif view
#

import urllib2
import urllib
from datetime import datetime
import xml.dom.minidom
import threading

import pygtk
pygtk.require("2.0")
import gtk
import gobject

import UDDI4Py.baseDOM as uddi
import UDDI4Py.client as uddi_client
import UDDI4Py.requestDOM as uddi_request
import UDDI4Py.responseDOM as uddi_response

import views
import darwincore2 as dwc2
from tables import tables
import digir

digir_search_lock = threading.Lock()

class DigirSearchThread(threading.Thread):
    
    def __init__(self, group=None, target=None, name=None, *args, **kwargs):#request, view, model):
        threading.Thread.__init__(self, group, target, name, args, kwargs)
        self.request = kwargs["request"]
        self.url = kwargs["url"]
        self.view = kwargs["view"]
        self.model = kwargs["model"]    
        self.gui = kwargs["gui"]    
    
        
    def run(self):
        global digir_search_lock
        digir_search_lock.acquire() # ********** critical
        url = self.url + "?doc=" + self.request
        self.gui.pulse_progressbar() # TODO: this doesn't work on the pb
        req = urllib2.Request(url)
        f = urllib2.urlopen(req)
        response = f.read()
        print response
        model = self.model
        gtk.threads_enter()
        dom = xml.dom.minidom.parseString(response)
        for record in dom.getElementsByTagName("record"):
            name_tags = record.getElementsByTagName("darwin:ScientificName")[0]
            # TODO: should be an easier way to get the text than this
            for node in name_tags.childNodes: # get the text node
                if node.nodeType == node.TEXT_NODE:
                    name = node.data
                    print name
                    model.append([name])
            
        print "set model"
        self.view.set_model(model)
        self.view.show_all()
        self.gui.stop_progressbar()
        gtk.threads_leave()
        digir_search_lock.release()
        

class GBIFView(views.View):
    
    # TODO: __name__ shouldn't really be here, meta information should be 
    # module level
    __name__ = "GBIFView" 
    
    pURL = "http://registry.gbif.net/uddi/inquiry"
    iURL = "http://registry.gbif.net/uddi/inquiry"
    
    def __init__(self, bauble):
        views.View.__init__(self)
        self.bauble = bauble
        self.create_gui()
        self.uddi_con = uddi_client.UDDIProxy(self.iURL,self.pURL)
        #self.test_tmodel()
        #self.get_missouri()
        #self.get_metadata()

    def search(self, row):
        """
        pass a dictionary of fields to values to lookup and display in the view
        """
        #url = "http://digir.mobot.org:80/digir/DiGIR.php"
        #resource = "MOBOT"
        url = "http://200.91.91.109/digir/DiGIR.php"
        resource = "atta"
        
        if type(row) == tables.Genera:
            print "searching genera"
            filter = """<equals>
            <darwin:Genus>
            %(genus)s
            </darwin:Genus>
            </equals>""" % {"genus": str(row)}
            print filter
            
        if type(row) == tables.Plantnames:
            print "searching plantnames"
        
        request = dwc2.search_request_template.substitute(filter=filter, 
                                                          sendtime=datetime.utcnow(),
                                                          destination=url,
                                                          resource=resource)            
        dom = xml.dom.minidom.parseString(unicode(request, "utf-8"))
        request = urllib.quote(dom.toxml())
        
        # TODO: if we used the thread module instead of threading we wouldn't
        # have to pass all this crap in, also wouldn't need a global lock 
        # object, what's the advantage of the threading module?
        thread = DigirSearchThread(url=url, request=request,
                                   model=gtk.ListStore(str),
                                   view=self.view, gui=self.bauble.gui)
        thread.start()
        
        
    def get_rowname(self, col, cell, model, iter):
        """
        return the string representation of some row inthe mode
        """
        row = model.get_value(iter, 0)
        if row is None:
            cell.set_property('text', "")
        else: cell.set_property('text', str(row))
    
        
    def create_gui(self):
        print "GBIFView.create_gui()"        
        self.view = gtk.TreeView()
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Name", renderer)
        column.set_cell_data_func(renderer, self.get_rowname)
        self.view.append_column(column)
        sw = gtk.ScrolledWindow()
        sw.add(self.view)
        self.add(sw)
        self.show_all()


    def urllib_get_response(self, url, data):
        import httplib
        httplib.HTTPConnection.debuglevel = 1
        import urllib2
        req = urllib2.Request(url, data)
        f = urllib2.urlopen(req)
        result = f.read()
        if hasattr(f, "headers"):
            print f.headers
        return result
        
        
    def httplib_get_response(self, data):
        import httplib
        conn = httplib.HTTPConnection("http://digir.mobot.org")
        pass

    
        
        
    def set_response(self, response):
        """
        """
        pass
        
    def get_metadata(self):
        import digir
        from datetime import datetime
        mobot_url = "http://digir.mobot.org/digir/DiGIR.php"
        request = digir.metadata_request_template.substitute(sendtime=datetime.utcnow(),
                                          destination=mobot_url)
        print request
        s = urllib.urlopen(mobot_url, request)
        response = s.read()
        print response
        
        
        
    def test_tmodel(self):
        tmodels = self.get_tmodels("DiGIR")
        for tmodel in tmodels:
            print tmodel
        #tmodel_key = tmodels[0].getTModelKey()
        
        
    def get_missouri(self):
        bizzes = self.get_businesses("Missouri")
        
        tmodels = self.get_tmodels("DiGIR")
        tmodel_key = tmodels[0].getTModelKey()
        
        for biz in bizzes:
            print "----------- business -------------"
            print biz
            service_infos = biz.getServiceInfos()
            services = service_infos.getServiceInfoNodes();
            for service in services:
                print "-------- service -------------"
                print service
                bindings = self.get_bindings(service.getServiceKey(), tmodel_key)
                for b in bindings:
                    print "-------- binding -------------"
                    print b
    
        
    def get_bindings(self, service_key, tmodel_key):
        try:
            request = uddi_request.findBinding()
            request.setServiceKey(service_key)
            tBag = uddi.tModelBag()
            tBag.setTModelKeyStrings([tmodel_key])
            request.setTModelBag(tBag)
            response = uddi_response.bindingDetail(self.uddi_con.send(request))
            return response.getBindingTemplateArray()

        except(socket.error, uddi.UDDIError), e:
            print e


    def get_tmodels(self, name):
        try:
            request = uddi_request.findTModel()
            request.setNameString(name)
            response = uddi_response.tModelList(self.uddi_con.send(request))
            infos = response.getTModelInfos()
            return infos.getTModelInfoNodes()
        except(socket.error, uddi.UDDIError), e:
            print e
    
    
    def get_services(self, business_key=None):
        try:
            request = uddi_request.findService()
            request.setBusinessKey(business_key)
            response = uddi_response.serviceList(self.uddi_con.send(request))
            infos = response.getServiceInfos()
            return infos.getServiceInfoArray()
        except(socket.error, uddi.UDDIError), e:
            print e
            
            
    def get_businesses(self, name="%"):
        try:
            request = uddi_request.findBusiness()
            request.setNameStrings(name)
            response = uddi_response.businessList(self.uddi_con.send(request))
            infos = response.getBusinessInfos()
            return infos.getBusinessInfoArray()
        except(socket.error, uddi.UDDIError), e:
            print e
        
    
