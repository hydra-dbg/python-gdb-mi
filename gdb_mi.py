import re, pprint
DIGITS = re.compile('\d+(\.\d+)?')

class ParsingError(Exception):
   def __init__(self, message, raw, error_found_at, include_context=True):
      if include_context:
         begin = (error_found_at-30) if error_found_at >= 30 else 0
         end   = (error_found_at+30)

         ctx = ", near context:\n  %s\n%s" % (raw[begin:end], " -" * 40)

      else:
         ctx = "."

      msg = "%s. Found at %i position%s\nOriginal message:\n  %s" % (message, error_found_at, ctx, raw)
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

def tuples_as_native_dict(tuples):
  native = {}
  for result in tuples:
     key, val = result.as_native_key_value()
     if key in native:
        if isinstance(native[key], list):
           native[key].append(val)
        else:
           native[key] = [native[key], val]
     else:
        native[key] = val

  return native

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
      return tuples_as_native_dict(self.value)

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


class Record:
    def is_stream(self, of_type=None):
        raise NotImplementedError("Subclass responsability")
    def is_async(self, of_type=None):
        raise NotImplementedError("Subclass responsability")
    def is_result(self, of_class=None):
        raise NotImplementedError("Subclass responsability")
    def __repr__(self):
        return pprint.pformat(self.as_native())

    def _rename_keywords(self, _dict):
        for k in ('class', 'type', 'token'):
            if k in _dict:
                _dict['_' + k] = _dict[k]
                del _dict[k]

class AsyncRecord(Record):
   Symbols = ("*", "+", "=")

   @check_end_of_input_at_begin
   def parse(self, string, offset):
      self.token = getattr(self, 'token', None)
      try:
         self.type = {
               "*": "Exec",
               "+": "Status",
               "=": "Notify",
               }[string[offset]]
      except KeyError:
         raise UnexpectedToken(string[offset], string, offset)

      offset += 1

      self.async_class = Word((',', '\r', '\n'))
      offset = self.async_class.parse(string, offset)
      self.async_class = self.async_class.as_native()

      self.results = []

      while string[offset] == ',':
         offset += 1
         self.results.append(Result())
         offset = self.results[-1].parse(string, offset)

      return offset

   def as_native(self, include_headers=True):
      native = tuples_as_native_dict(self.results)
      self._rename_keywords(native)

      if not include_headers:
          return native

      native['class'] = self.async_class
      native['type'] = self.type
      native['token'] = self.token
      return native

   def is_async(self, of_type=None):
       if of_type is None:
           return True

       if isinstance(of_type, (tuple,list,set)):
           return self.type in of_type
       elif isinstance(of_type, (str,bytes)):
           return self.type == of_type

       raise ValueError("Invalid argument. Expected tuple/list/set, str or None")

   def is_stream(self, of_type=None):
       return False
   def is_result(self, of_class=None):
       return False

class StreamRecord(Record):
   Symbols = ("~", "@", "&")

   @check_end_of_input_at_begin
   def parse(self, string, offset):
      if not string[offset] in StreamRecord.Symbols:
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

   def as_native(self, include_headers=True):
      native = {'value': self.value.as_native()}
      if not include_headers:
         return native

      native['type'] = self.type
      return native

   def is_stream(self, of_type=None):
       if of_type is None:
           return True

       if isinstance(of_type, (tuple,list,set)):
           return self.type in of_type
       elif isinstance(of_type, (str,bytes)):
           return self.type == of_type

       raise ValueError("Invalid argument. Expected tuple/list/set, str or None")

   def is_async(self, of_type=None):
       return False
   def is_result(self, of_class=None):
       return False


class ResultRecord(Record):
   Symbols = ("^",)

   @check_end_of_input_at_begin
   def parse(self, string, offset):
      self.token = getattr(self, 'token', None)
      self.type = 'Result'
      if not string[offset] in ResultRecord.Symbols:
         raise UnexpectedToken(string[offset], string, offset)
      offset += 1

      self.result_class = Word((',', '\r', '\n'))
      offset = self.result_class.parse(string, offset)

      self.result_class = self.result_class.as_native()

      self.results = []

      while string[offset] == ',':
         offset += 1
         self.results.append(Result())
         offset = self.results[-1].parse(string, offset)

      return offset

   def is_result(self, of_class=None):
       if of_class is None:
           return True

       _class = self.result_class
       if isinstance(of_class, (tuple,list,set)):
           return _class in of_class
       elif isinstance(of_class, (str,bytes)):
           return _class == of_class

       raise ValueError("Invalid argument. Expected tuple/list/set, str or None")

   def is_stream(self, of_type=None):
       return False
   def is_async(self, of_type=None):
       return False

   def as_native(self, include_headers=True):
      native = tuples_as_native_dict(self.results)

      self._rename_keywords(native)
      if not include_headers:
          return native

      native['class'] = self.result_class
      native['type'] = self.type
      native['token'] = self.token
      return native

class TerminationRecord(Record):
    def is_stream(self, of_type=None):
        return False
    def is_async(self, of_type=None):
        return False
    def is_result(self, of_class=None):
        return False
    def __repr__(self):
        return repr("(gdb)")
    def __eq__(self, other):
        return other == "(gdb)"
    def __ne__(self, other):
        return other != "(gdb)"
    def __hash__(self):
        return hash("(gdb)")

_TerminationRecordObj = TerminationRecord()

class Output:
   def __init__(self, nl='\n'):
      self._line = None
      self._chunks = []
      self._more_lines_in_buffer = False
      self._nl = nl
      assert self._nl

      self._termination = "(gdb) " + self._nl

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
      assert line.endswith(self._nl)

      #import pdb; pdb.set_trace()        #     :)
      #if "BreakpointTable" in line:
      #   import pdb; pdb.set_trace()        #     :)

      #XXX the space between the string and the newline is not specified in the
      # GDB's documentation. However it's seems to be necessary.
      if line == self._termination:
         # we always return this special record instance
         return _TerminationRecordObj

      # StreamRecords don't have a token, so we can parse them right here
      if line[0] in StreamRecord.Symbols:
         out = StreamRecord()
         out.parse(line, 0)
         return out

      # parse the token, if any
      token = DIGITS.match(line)
      offset = 0
      if token:
         token = token.group()
         offset += len(token)
         token = int(token)

      else:
         token = None

      # Result/Async Record time
      if line[offset] in ResultRecord.Symbols:
         out = ResultRecord()
      elif line[offset] in AsyncRecord.Symbols:
         out = AsyncRecord()
      else:
         raise ParsingError("Invalid input. Maybe the target's output is interfering with the GDB MI's messages. Try to redirect the target's output to elsewhere or run GDB's 'set new-console on' command",
                    line[:72], offset, include_context=False)


      # ###############
      # Workaround: handle the GDB's bug https://sourceware.org/bugzilla/show_bug.cgi?id=14733
      if "BreakpointTable={" in line:
         # We remove the "bkpt=" string to trick the system and transform the body of the BreakpointTable 
         # into an array or list of dictionaries.
         line = line.replace("bkpt=", "")

      if "^done,bkpt={" in line:
         line = line.replace("^done,bkpt={", "^done,bkpts=[{")
         line = line[:-len(self._nl)] + "]" + self._nl
      elif "=breakpoint-modified,bkpt={" in line:
         line = line.replace("=breakpoint-modified,bkpt={", "=breakpoints-modified,bkpts=[{")
         line = line[:-len(self._nl)] + "]" + self._nl

      #
      ################

      offset = out.parse(line, offset)
      next_offset = offset + len(self._nl)

      if len(line) != next_offset:
          raise ParsingError("Length line %i is different from the last parsed offset %i" % (len(line), next_offset),
                  line, offset)

      record = out
      record.token = token
      return record

