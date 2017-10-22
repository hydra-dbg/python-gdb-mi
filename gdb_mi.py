import re, pprint
DIGITS = re.compile('\d+(\.\d+)?')

class ParsingError(Exception):
   def __init__(self, message, raw, error_found_at):
      begin = (error_found_at-30) if error_found_at >= 30 else 0
      end   = (error_found_at+30)

      msg = "%s. Found near:\n  %s\n%s\nOriginal message:\n  %s" % (message, raw[begin:end], " -" * 40, raw)
      Exception.__init__(self, msg)

class UnexpectedToken(ParsingError):
   def __init__(self, token, raw, error_found_at):
      msg = "Unexpected token '%c'." % token
      ParsingError.__init__(self, msg, raw, error_found_at)


def check_end_of_input_at_begin(func):
   def wrapper(self, string, offset):
      if len(string) > offset:
         return func(self, string, offset)
      else:
         raise ParsingError("End of input.", string, offset)

   return wrapper

def _attributes_as_string(instance):
   attrnames = filter(lambda attrname: not attrname.startswith("_"), dir(instance))
   attrnames = filter(lambda attrname: not callable(getattr(instance, attrname)), attrnames)
   
   return pprint.pformat(dict([(attrname, getattr(instance, attrname)) for attrname in attrnames]))

def text_escape(bytes_or_str):
   if isinstance(bytes_or_str, bytes):
      return bytes_or_str.decode('string_escape')
   else:
      return bytes_or_str.encode('ascii').decode('unicode_escape')

class Result:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      self.variable = Variable()
      offset = self.variable.parse(string, offset)

      if not string[offset] == '=':
         raise UnexpectedToken(string[offset], string, offset)

      offset += 1

      self.value = Value()
      offset = self.value.parse(string, offset)

      return offset

   def as_native(self):
      return {self.variable.as_native(): self.value.as_native()}

   def as_native_key_value(self):
      return (self.variable.as_native(), self.value.as_native())

   def __repr__(self):
      return str(self.variable) + " = " + _attributes_as_string(self.value)


class Variable:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      i = string[offset:].find('=')
      if i < 0:
         raise ParsingError("Token '=' not found.", string, offset)

      self.name = string[offset:offset+i]

      return offset+i

   def as_native(self):
      return self.name

   def __repr__(self):
      return self.name


class Value:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      c = string[offset]

      try:
         self.value = {
               '"': CString(),
               '{': Tuple(),
               '[': List(),
               }[c]
      except KeyError:
         raise UnexpectedToken(c, string, offset)

      offset = self.value.parse(string, offset)
      return offset

   def as_native(self):
      return self.value.as_native()

   def __repr__(self):
      return pprint.pformat(self.as_native())

class CString:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      if not string[offset] == '"':
         raise ParsingError("Wrong begin. Expected a double quote '\"'.", string, offset)

      end = False
      
      escaped = False
      for i, c in enumerate(string[offset+1:]):
         if c == '"' and not escaped:
            self.value = text_escape(string[offset+1:offset+1+i])
            consumed = i
            end = True
            break

         if c == '\\':
            escaped = not escaped
         else:
            escaped = False

      if not end:
         raise ParsingError("End of input found without close the c-string. Expecting a '\"'.", string, offset)

      return offset + consumed + 2

   def as_native(self):
      return self.value

   def __repr__(self):
      return pprint.pformat(self.as_native())


class Tuple:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      if not string[offset] == '{':
         raise ParsingError("Wrong begin. Expected a '{'.", string, offset)

      self.value = []
      
      offset += 1
      while string[offset] != '}':
         self.value.append(Result())
         offset = self.value[-1].parse(string, offset)

         if offset >= len(string):
            raise ParsingError("End of input found without close the tuple (aka dictionary). Expecting a '}'.", string, offset)

         if not string[offset] in (",", "}"):
            raise UnexpectedToken(string[offset], string, offset)

         if string[offset] == ",":
            offset += 1


      return offset + 1

   def as_native(self):
      native = {}
      for result in self.value:
         key, val = result.as_native_key_value()
         if key in native:
            if isinstance(native[key], list):
               native[key].append(val)
            else:
               native[key] = [native[key], val]
         else:
            native[key] = val

      return native

   def __repr__(self):
      return pprint.pformat(self.as_native())

class List:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      if not string[offset] == '[':
         raise ParsingError("Wrong begin. Expected a '['.", string, offset)

      self.value = []
      
      offset += 1

      if string[offset] != ']':
         Elem = Value if string[offset] in ('"', '{', '[') else Result

      while string[offset] != ']':
         self.value.append(Elem())
         offset = self.value[-1].parse(string, offset)

         if offset >= len(string):
            raise ParsingError("End of input found without close the list. Expecting a ']'.", string, offset)

         if not string[offset] in (",", "]"):
            raise UnexpectedToken(string[offset], string, offset)

         if string[offset] == ",":
            offset += 1


      return offset + 1
   
   def as_native(self):
      return [val.as_native() for val in self.value]

   def __repr__(self):
      return pprint.pformat(self.as_native())

class Word:
   def __init__(self, delimiters):
      self.delimiters = delimiters

   @check_end_of_input_at_begin
   def parse(self, string, offset):
      i = 0
      while string[offset+i] not in self.delimiters:
         i += 1

      self.value = string[offset:offset+i]
      return offset + i


   def as_native(self):
      return self.value

   def __repr__(self):
      return pprint.pformat(self.as_native())


class AsyncOutput:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      self.async_class = Word((',', '\r', '\n'))
      offset = self.async_class.parse(string, offset)

      self.results = []

      while string[offset] == ',':
         offset += 1
         self.results.append(Result())
         offset = self.results[-1].parse(string, offset)

      return offset

   def as_native(self):
      native = {}
      for result in self.results:
         key, val = result.as_native_key_value()
         if key in native:
            if isinstance(native[key], list):
               native[key].append(val)
            else:
               native[key] = [native[key], val]
         else:
            native[key] = val

      
      return Record(klass= self.async_class.as_native(),
               results=native)

   def __repr__(self):
      return pprint.pformat(self.as_native())

class AsyncRecord:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      try:
         self.type = {
               "*": "Exec",
               "+": "Status",
               "=": "Notify",
               }[string[offset]]
      except KeyError:
         raise UnexpectedToken(string[offset], string, offset)

      offset += 1
      self.output = AsyncOutput()
      offset = self.output.parse(string, offset)

      return offset

   def as_native(self):
      d = self.output.as_native()
      d.type = self.type
      return d

   def __repr__(self):
      return pprint.pformat(self.as_native())

class StreamRecord:
   @check_end_of_input_at_begin
   def parse(self, string, offset):
      if not string[offset] in ("~", "@", "&"):
         raise UnexpectedToken(string[offset], string, offset)

      try:
         self.type = {
               "~": "Console",
               "@": "Target",
               "&": "Log",
               }[string[offset]]
      except KeyError:
         raise UnexpectedToken(string[offset], string, offset)

      offset += 1
      self.value = CString()
      offset = self.value.parse(string, offset)

      return offset

   def as_native(self):
      return Stream(self.type, self.value.as_native())

   def __repr__(self):
      return pprint.pformat(self.as_native())

class Stream:
   def __init__(self, type, s):
      self.type = type
      self.stream = s

   def __repr__(self):
      return _attributes_as_string(self)

   def as_native(self):
      return vars(self)

class ResultRecord:

   @check_end_of_input_at_begin
   def parse(self, string, offset):
      if not string[offset] == "^":
         raise UnexpectedToken(string[offset], string, offset)
      offset += 1

      self.result_class = Word((',', '\r', '\n'))
      offset = self.result_class.parse(string, offset)

      self.results = []

      while string[offset] == ',':
         offset += 1
         self.results.append(Result())
         offset = self.results[-1].parse(string, offset)

      return offset

   def as_native(self):
      native = {}
      for result in self.results:
         key, val = result.as_native_key_value()
         if key in native:
            if isinstance(native[key], list):
               native[key].append(val)
            else:
               native[key] = [native[key], val]
         else:
            native[key] = val

      r = Record( klass = self.result_class.as_native(), 
                  results = native)
      r.type = 'Sync'
      return r

   def __repr__(self):
      return pprint.pformat(self.as_native())

class Record:
   def __init__(self, klass, results):
      self.klass = klass
      self.results = results
      
      self.token = None
      self.type = None

   def __repr__(self):
      return _attributes_as_string(self)


class Output:
   def __init__(self):
      self._line = None
      self._chunks = []
      self._more_lines_in_buffer = False

   def are_more_to_be_parsed_already(self):
      return self._more_lines_in_buffer

   def parse(self, chunk):
      if self._more_lines_in_buffer:
          chunk = self._chunks[-1] + chunk
          del self._chunks[-1]
          self._more_lines_in_buffer = False

      if '\n' in chunk:
          tail, rest = chunk.split('\n', 1)
          line = ''.join(self._chunks + [tail, '\n'])
          self._chunks = []
          self._more_lines_in_buffer = False

          if rest:
              self._chunks.append(rest)
          
          if '\n' in rest:
              self._more_lines_in_buffer = True

          record = self.parse_line(line)
          assert record is not None
          return record
      
      else:
          self._chunks.append(chunk)
          return None
      
   def parse_line(self, line):
      assert line[-1] == '\n'

      #import pdb; pdb.set_trace()        #     :)  
      #if "BreakpointTable" in line:
      #   import pdb; pdb.set_trace()        #     :)  

      #XXX the space between the string and the newline is not specified in the
      # GDB's documentation. However it's seems to be necessary.
      if line == "(gdb) \n": 
         # we always return this string
         return "(gdb)" 

      if line[0] in ("~", "@", "&"):
         out = StreamRecord()
         out.parse(line, 0)
         return out.as_native()

      # ###############
      # Workaround: handle the GDB's bug https://sourceware.org/bugzilla/show_bug.cgi?id=14733
      if "BreakpointTable={" in line:
         # We remove the "bkpt=" string to trick the system and transform the body of the BreakpointTable 
         # into an array or list of dictionaries.
         line = line.replace("bkpt=", "")

      if "^done,bkpt={" in line:
         line = line.replace("^done,bkpt={", "^done,bkpts=[{")
         line = line[:-1] + "]\n"
      elif "=breakpoint-modified,bkpt={" in line:
         line = line.replace("=breakpoint-modified,bkpt={", "=breakpoints-modified,bkpts=[{")
         line = line[:-1] + "]\n"

      #
      ################
              
      token = DIGITS.match(line)
      offset = 0
      if token:
         token = token.group()
         offset += len(token)
         token = int(token)

      else:
         token = None

      if line[offset] == "^":
         out = ResultRecord()
      else:
         out = AsyncRecord()

      offset = out.parse(line, offset)

      if len(line) != offset + 1:
          raise ParsingError("Length line %i is different from the last parsed offset %i" % (len(line), offset+1),
                  line, offset)

      record = out.as_native()
      record.token = token
      return record




