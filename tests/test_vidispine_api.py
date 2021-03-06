# *-* coding: UTF-8 --*

import unittest2
from mock import MagicMock, patch
import http.client
import base64
import logging
import tempfile
from os import urandom
from http.client import CannotSendRequest

class TestVSApi(unittest2.TestCase):
    fake_host='localhost'
    fake_port=8080
    fake_user='username'
    fake_passwd='password'
    
    class MockedResponse(object):
        def __init__(self, status_code, content, reason=""):
            self.status = status_code
            self.body = content
            self.reason = reason
            
        def read(self):
            return self.body
        
    def test_get(self):
        """
        test a simple HTTP get request
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi
        sample_returned_xml = """<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <element>string</element>
        </root>"""
        
        conn = http.client.HTTPConnection(host='localhost',port=8080)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(200,sample_returned_xml))
        
        api = VSApi(user=self.fake_user,passwd=self.fake_passwd,conn=conn)
        parsed_xml = api.request("/path/to/endpoint",method="GET")

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('GET','/API/path/to/endpoint', None, {'Authorization': "Basic " + computed_auth.decode("UTF-8"), 'Accept': 'application/xml'})
        conn.getresponse.assert_called_with()
        
        teststring = parsed_xml.find('{0}element'.format("{http://xml.vidispine.com/schema/vidispine}"))
        self.assertEqual(teststring.text,"string")

    def test_put(self):
        """
        test a simple HTTP put request
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi
        sample_send_xml = b"""<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <element>string</element>
        </root>"""
        
        sample_returned_xml = """<?xml version="1.0"?>
        <response xmlns="http://xml.vidispine.com/schema/vidispine">
          <returned-element>string</returned-element>
        </response>
        """
        conn = http.client.HTTPConnection(host=self.fake_host, port=self.fake_port)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(200, sample_returned_xml)) #simulate empty OK response
    
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        parsed_xml = api.request("/path/to/endpoint", method="PUT", body=sample_send_xml)

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('PUT', '/API/path/to/endpoint', sample_send_xml,
                                        {'Content-Type': 'application/xml', 'Authorization': "Basic " + computed_auth.decode("UTF-8"), 'Accept': 'application/xml'})
        conn.getresponse.assert_called_with()

        teststring = parsed_xml.find('{0}returned-element'.format("{http://xml.vidispine.com/schema/vidispine}"))
        self.assertEqual(teststring.text, "string")
        
    def test_post(self):
        """
        test a simple HTTP post request
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi
        sample_send_xml = b"""<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <element>string</element>
        </root>"""
    
        conn = http.client.HTTPConnection(host=self.fake_host, port=self.fake_port)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(201, ""))  # simulate empty OK response
    
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        api.request("/path/to/endpoint", method="POST", body=sample_send_xml)

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('POST', '/API/path/to/endpoint', sample_send_xml,
                                        {'Content-Type': 'application/xml', 'Authorization': "Basic " + computed_auth.decode("UTF-8"),
                                         'Accept'      : 'application/xml'})
        conn.getresponse.assert_called_with()
        
    def test_404(self):
        from gnmvidispine.vidispine_api import VSApi, VSNotFound, HTTPError
        
        exception_response = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExceptionDocument xmlns="http://xml.vidispine.com/schema/vidispine">
  <notFound>
    <type>Item</type>
    <id>SD-46362</id>
  </notFound>
</ExceptionDocument>"""
        
        conn = http.client.HTTPConnection(host='localhost', port=8080)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(404, exception_response, reason="Test 404 failure"))
    
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        
        with self.assertRaises(VSNotFound) as ex:
            api.request("/item/SD-46362/metadata", method="GET")

        self.assertEqual("SD-46362",ex.exception.exceptionID)
        self.assertEqual("notFound",ex.exception.exceptionType)
        self.assertEqual("no explanation provided",ex.exception.exceptionWhat)

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('GET', '/API/item/SD-46362/metadata', None,
                                        {'Authorization': "Basic " + computed_auth.decode("UTF-8"), 'Accept': 'application/xml'})
        conn.getresponse.assert_called_with()
        
    def test_400(self):
        """
        test the VSBadRequest exception, including error parsing
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi, VSBadRequest
        request_body = b"""<MetadataDocument xmlns="http://xml.vidispine.com/">
  <field>
    <name>blah</name>
    <value>smith</value>
  </field>
</MetadataDocument>"""  #invalid namespace will raise bad request error
        exception_response = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ExceptionDocument xmlns="http://xml.vidispine.com/schema/vidispine"><invalidInput><context>metadata</context><id>VX-3245</id><explanation>Couldn't transform the input according to the projection.</explanation></invalidInput></ExceptionDocument>"""

        conn = http.client.HTTPConnection(host='localhost', port=8080)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(400, exception_response, reason="Test 40- failure"))
    
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
    
        with self.assertRaises(VSBadRequest) as ex:
            api.request("/item/VX-3245/metadata", method="PUT", body=request_body)
    
        self.assertEqual("VX-3245", ex.exception.exceptionID)
        self.assertEqual("invalidInput", ex.exception.exceptionType)
        self.assertEqual("Couldn't transform the input according to the projection.", ex.exception.exceptionWhat)

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('PUT', '/API/item/VX-3245/metadata', request_body,
                                        {'Content-Type': 'application/xml', 'Authorization': "Basic " + computed_auth.decode("UTF-8"), 'Accept': 'application/xml'})
        
    def test_503(self):
        """
        test the exponential backoff/retry if server not available
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi,HTTPError
        from time import time
        
        conn = http.client.HTTPConnection(host=self.fake_host, port=self.fake_port)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(503, "No server available"))

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("gnmvidispine.vidispine_api")
        logger.error = MagicMock()
        logger.warning = MagicMock()
        
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn, logger=logger)
        api.retry_delay=1
        api.retry_attempts=5
        
        start_time = time()
        with self.assertRaises(HTTPError) as cm:
            api.request("/path/to/endpoint", method="GET")

        end_time = time()

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('GET', '/API/path/to/endpoint', None,
                                        {'Authorization': "Basic " + computed_auth.decode("UTF-8"), 'Accept': 'application/xml'})
        conn.getresponse.assert_called_with()

        self.assertEqual(cm.exception.code, 503)
        self.assertGreaterEqual(end_time - start_time, api.retry_delay * api.retry_attempts)
        
        logger.warning.assert_called_with('Server not available error when contacting Vidispine. Waiting 1s before retry.')
        self.assertEqual(logger.warning.call_count, 6)
        
        logger.error.assert_called_with('Did not work after 5 retries, giving up')
        
    def test_409(self):
        """
        tests the VSConflict exception
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi, VSConflict

        exception_response = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExceptionDocument xmlns="http://xml.vidispine.com/schema/vidispine">
  <conflict>
    <type>Item</type>
    <id>SD-46362</id>
  </conflict>
</ExceptionDocument>"""
        conn = http.client.HTTPConnection(host=self.fake_host, port=self.fake_port)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(409, exception_response, reason="Test 409 failure"))
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        with self.assertRaises(VSConflict) as ex:
            api.request("/item/VX-3245/metadata", method="GET")
        self.assertEqual("SD-46362", ex.exception.exceptionID)
        self.assertEqual("conflict", ex.exception.exceptionType)

    def test_chunked_upload(self):
        """
        test the chunked_upload_request functionality
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi,HTTPError
        
        conn = http.client.HTTPConnection(host=self.fake_host, port=self.fake_port)
        conn.request = MagicMock()
        
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("gnmvidispine.vidispine_api")
        logger.error = MagicMock()
        logger.warning = MagicMock()
        logger.debug = MagicMock()
        
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn, logger=logger)
        api.raw_request = MagicMock()

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))

        #create a test file
        testfilesize = 100000
        testchunksize = 1000
        
        class FakeUuid4(object):
            """
            mock object to return a known id. used via mock.patch below.
            """
            def get_hex(self):
                return 'fa6032d61c7b4db19425c6404ea7b822'
            
        with tempfile.TemporaryFile() as f:
            filecontent = bytes(urandom(testfilesize))
            f.write(filecontent)
            with patch('uuid.uuid4', side_effect=lambda: FakeUuid4()):
                api.chunked_upload_request(f, testfilesize, testchunksize, '/API/fakeupload', matrix=None, transferPriority=100, throttle=False,
                                           method="POST", filename="fakefile.dat", extra_headers={'extra_header': 'true'})
                
                should_have_headers = {
                    'Authorization': "Basic " + computed_auth.decode("UTF-8"),
                    'Content-Type': 'application/octet-stream',
                    'Accept': 'application/xml'
                }

                for byteindex in range(0,testfilesize,testchunksize):
                    should_have_qparams = {
                        'transferId': 'fa6032d61c7b4db19425c6404ea7b822',
                        'transferPriority': 100,
                        'throttle': False,
                        'filename': 'fakefile.dat'
                    }
                    should_have_extra_headers = {
                        'index': byteindex,
                        'size': 100000,
                    }

                    api.raw_request.assert_any_call('/API/fakeupload', matrix=None, body=filecontent[byteindex:byteindex+testchunksize],
                                                        content_type='application/octet-stream', method="POST",
                                                        query=should_have_qparams, rawData=True ,extra_headers=should_have_extra_headers)

                self.assertEqual(api.raw_request.call_count, 100)

    def test_reuse(self):
        from gnmvidispine.vidispine_api import VSApi
        conn = http.client.HTTPConnection(host='localhost',port=8080)
        conn.request = MagicMock(side_effect=CannotSendRequest())
        
        a = VSApi(host='localhost',user='testuser',passwd='testpasswd',conn=conn)
        a.reset_http = MagicMock()
        
        with patch('time.sleep') as sleepmock:  #mocking sleep() makes the test run faster
            with self.assertRaises(CannotSendRequest):
                a.sendAuthorized('GET','/fake_path',"",{})
        self.assertEqual(a.reset_http.call_count,11)
        self.assertEqual(sleepmock.call_count,11)
    
    def test_reset_http(self):
        from gnmvidispine.vidispine_api import VSApi
        conn = http.client.HTTPConnection(host='localhost', port=8080)
        conn.close = MagicMock()

        a = VSApi(host='localhost', user='testuser', passwd='testpasswd', conn=conn)
        a.reset_http()
        conn.close.assert_called_once()
        self.assertNotEqual(conn,a._conn) #we should get a different object

    def test_querydict(self):
        from gnmvidispine.vidispine_api import VSApi
        from collections import OrderedDict
        sample_returned_xml = """<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <element>string</element>
        </root>"""

        conn = http.client.HTTPConnection(host='localhost', port=8080)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(200, sample_returned_xml))

        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        queryparams = OrderedDict({
            'query2': 'value2',
            'query3': ['value3','value4','value5'],
            'query1': 'value1',
            'query4': 37
        })
        parsed_xml = api.request("/path/to/endpoint", query=queryparams, method="GET")

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('GET', '/API/path/to/endpoint?query2=value2&query3=value3&query3=value4&query3=value5&query1=value1&query4=37', None,
                                        {'Authorization': "Basic " + computed_auth.decode("UTF-8"), 'Accept': 'application/xml'})
        conn.getresponse.assert_called_with()

    def test_matrixdict(self):
        from gnmvidispine.vidispine_api import VSApi
        sample_returned_xml = """<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <element>string</element>
        </root>"""

        conn = http.client.HTTPConnection(host='localhost', port=8080)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(200, sample_returned_xml))

        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        mtxparams={
            'mtx4': 8,
            'mtx3': ['value3','value4','value5'],
            'mtx2': 'value2',
            'mtx1': 'value1'
        }

        parsed_xml = api.request("/path/to/endpoint", matrix=mtxparams, method="GET")

        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        conn.request.assert_called_with('GET', '/API/path/to/endpoint;mtx4=8;mtx3=value3;mtx3=value4;mtx3=value5;mtx2=value2;mtx1=value1', None,
                                        {'Authorization': "Basic " + computed_auth.decode("UTF-8"), 'Accept': 'application/xml'})
        conn.getresponse.assert_called_with()

    def test_find_portal_data_none(self):
        """
        find_portal_data should be able to handle a null value if extra portal data does not exist on a field
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi
        from xml.etree.cElementTree import Element, SubElement

        fake_elem = MagicMock(target=Element)
        test_elem = Element("data")

        api = VSApi(user=self.fake_user, passwd=self.fake_passwd)
        api.findPortalDataNode = MagicMock(return_value=test_elem)
        self.assertEqual(api.findPortalData(fake_elem), None)

    def test_unicode_body(self):
        """
        sendAuthorized should be able to handle unicode characters in the request body
        :return:
        """
        dodgy_string = """<?xml version='1.0' encoding='UTF-8'?>
<MetadataDocument xmlns="http://xml.vidispine.com/schema/vidispine"><timespan end="+INF" start="-INF"><field><name>title</name><value>Thousands take to streets in Barcelona to protest against police violence – video </value></field><field><name>gnm_asset_category</name><value>Master</value></field><field><name>gnm_type</name><value>Master</value></field><fiel"""

        from gnmvidispine.vidispine_api import VSApi
        from http.client import HTTPConnection
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd)
        authstring = u"{0}:{1}".format(self.fake_user, self.fake_passwd)
        computed_auth = base64.b64encode(authstring.encode("UTF-8"))
        #auth = base64.encodestring('%s:%s' % (self.fake_user, self.fake_passwd)).replace('\n', '')

        api._conn = MagicMock(target=HTTPConnection)

        api.sendAuthorized("GET","/path/to/fake/url", dodgy_string,{})
        api._conn.request.assert_called_once_with("GET",
                                                  "/path/to/fake/url",
                                                  b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<MetadataDocument xmlns="http://xml.vidispine.com/schema/vidispine"><timespan end="+INF" start="-INF"><field><name>title</name><value>Thousands take to streets in Barcelona to protest against police violence \xe2\x80\x93 video </value></field><field><name>gnm_asset_category</name><value>Master</value></field><field><name>gnm_type</name><value>Master</value></field><fiel',
                                                  {'Authorization': 'Basic ' + computed_auth.decode("UTF-8")}
                                                  )

    def test_param_list_unicode(self):
        from gnmvidispine.vidispine_api import VSApi
        response = VSApi._get_param_list("keyname","arséne wenger est allée en vacances. Häppy hølidåys")
        #ensure that the unicode string has been urlencoded properly
        self.assertEqual(response, ['keyname=ars%C3%A9ne%20wenger%20est%20all%C3%A9e%20en%20vacances.%20H%C3%A4ppy%20h%C3%B8lid%C3%A5ys'])

    def test_escape_for_query(self):
        """
        _escape_for_query should not blow up if it's given unicode text
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi

        VSApi._escape_for_query("/srv/Multimedia2/Media Production/Assets/Multimedia_News/FEARLESS_women_in_India/ekaterina_ochagavia_FEARLESS_women_in_India_2/ASSETS/SOME MUSIC/IRENE/ES_Colored Spirals 4 - Johannes Bornlöf/ES_Colored Spirals 4 STEMS DRUMS.mp3")

    def test_set_metadata(self):
        from gnmvidispine.vidispine_api import VSApi
        sample_returned_xml = """<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <element>string</element>
        </root>"""
        conn = http.client.HTTPConnection(host='localhost', port=8080)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(200, sample_returned_xml))
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        api.set_metadata('/VX-1234', {'test': '1', 'anothertest': '2'})

        arg1, arg2, arg3, arg4 = conn.request.call_args[0]
        test_dict = arg4
        self.assertEqual(arg1, 'PUT')
        self.assertEqual(arg2, '/API/VX-1234/metadata')
        self.assertEqual(arg3, b'<SimpleMetadataDocument xmlns="http://xml.vidispine.com/schema/vidispine">\n<field><key>test</key><value>1</value></field>\n<field><key>anothertest</key><value>2</value></field></SimpleMetadataDocument>')
        self.assertEqual(test_dict['Accept'], 'application/xml')
        self.assertEqual(test_dict['Content-Type'], 'application/xml')
        self.assertEqual(test_dict['Authorization'], 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=')

    def test_set_metadata_add(self):
        from gnmvidispine.vidispine_api import VSApi
        sample_returned_xml = """<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <element>string</element>
        </root>"""
        conn = http.client.HTTPConnection(host='localhost', port=8080)
        conn.request = MagicMock()
        conn.getresponse = MagicMock(return_value=self.MockedResponse(200, sample_returned_xml))
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, conn=conn)
        api.set_metadata('/VX-1234', {'test': '1', 'anothertest': '2'}, mode='add')

        arg1, arg2, arg3, arg4 = conn.request.call_args[0]
        test_dict = arg4
        self.assertEqual(arg1, 'PUT')
        self.assertEqual(arg2, '/API/VX-1234/metadata')
        self.assertEqual(arg3, b'<SimpleMetadataDocument xmlns="http://xml.vidispine.com/schema/vidispine">\n<field><key>test</key><value mode="add">1</value></field>\n<field><key>anothertest</key><value mode="add">2</value></field></SimpleMetadataDocument>')
        self.assertEqual(test_dict['Accept'], 'application/xml')
        self.assertEqual(test_dict['Content-Type'], 'application/xml')
        self.assertEqual(test_dict['Authorization'], 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=')

    def test_get_metadata(self):
        import xml.etree.cElementTree as ET
        sample_xml = """<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <field>
            <name>string</name>
            <value>test</value>
          </field>
          <field>
            <name>something</name>
            <value>wibble</value>
          </field>
          <field>
            <name>text</name>
            <value>some text</value>
          </field>
        </root>"""

        with patch("gnmvidispine.vidispine_api.VSApi.request", return_value=ET.fromstring(sample_xml)) as mock_request:
            from gnmvidispine.vidispine_api import VSApi
            api = VSApi(user=self.fake_user, passwd=self.fake_passwd)
            meta_dict = api.get_metadata('VX-1234')
            self.assertEqual(meta_dict['string'], 'test')
            self.assertEqual(meta_dict['something'], 'wibble')
            self.assertEqual(meta_dict['text'], 'some text')

        more_xml = """<?xml version="1.0"?>
        <root xmlns="http://xml.vidispine.com/schema/vidispine">
          <timespan>
            <field>
              <name>string</name>
              <value>test</value>
            </field>
            <field>
              <name>something</name>
              <value>wibble</value>
            </field>
            <field>
              <name>text</name>
              <value>some text</value>
            </field>
          </timespan>
        </root>"""

        with patch("gnmvidispine.vidispine_api.VSApi.request", return_value=ET.fromstring(more_xml)) as mock_request:
            from gnmvidispine.vidispine_api import VSApi
            api = VSApi(user=self.fake_user, passwd=self.fake_passwd)
            meta_dict = api.get_metadata('VX-1234')
            self.assertEqual(meta_dict['string'], 'test')
            self.assertEqual(meta_dict['something'], 'wibble')
            self.assertEqual(meta_dict['text'], 'some text')

    def test_always_string(self):
        """
        Test always_string can cope with various object types and that is outputs the expected strings
        :return:
        """
        from gnmvidispine.vidispine_api import always_string

        always_string_output = always_string(1)
        self.assertEqual(always_string_output, '1')
        always_string_output = always_string('Wibble')
        self.assertEqual(always_string_output, 'Wibble')
        always_string_output = always_string(b'Wibble, Wibble')
        self.assertEqual(always_string_output, 'Wibble, Wibble')
        always_string_output = always_string(1.1)
        self.assertEqual(always_string_output, '1.1')
        always_string_output = always_string(True)
        self.assertEqual(always_string_output, 'True')

    def test_https(self):
        """
        Test if an HTTPS connection can be started
        :return:
        """
        from gnmvidispine.vidispine_api import VSApi
        api = VSApi(user=self.fake_user, passwd=self.fake_passwd, https=True)
