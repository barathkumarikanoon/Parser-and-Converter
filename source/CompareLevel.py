import re
import logging


ARTICLE      = 4
DECIMAL      = 3
SMALLSTRING  = 2
GENSTRING    = 1
ROMAN        = 0

class CompareLevel:
    def __init__(self, val, depthType):
        self.logger = logging.getLogger(__name__)
        self.depthTypes = [depthType, -1, -1, -1, -1,-1]
        self.valnum     = [val, None, None, None, None,None]   
        self.nextvals =  self.get_next_vals()

    def get_next_vals(self):
        nextvals = {}

        try:
            nextvals[DECIMAL] = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10',\
                                '11', '12', '13', '14', '15', '16', '17', '18', '19', '20']
            nextvals[ROMAN]   = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',\
                                'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx']
            nextvals[SMALLSTRING]  = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',\
                                    'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
            nextvals[GENSTRING] = []
            for valueType in list(nextvals.keys()):
                i = 0
                x = {}
                for a in nextvals[valueType]:
                    x[a] = i
                    i+= 1
                nextvals[valueType] = x
        except Exception as e:
            self.logger.error(f"Failed in get_next_vals: {e}")
        return nextvals

    def is_next_val(self, nextval, value1, value2):
        self.logger.debug(f"Comparing: {value1} -> {value2} in nextval[{type}]")
        if value1 in nextval and value2 in nextval and nextval[value2] == nextval[value1] + 1:
            return True
        else:
            return False

    def is_roman(self, number):
        self.logger.debug(f"Checking Roman: {number}")

        try:
            s = str(number).upper().strip()

            roman_pattern = (
                r"(X{0,3})"
                r"(IX|IV|V?I{0,3})$"
            )

            if not re.match(roman_pattern, s):
                return False

            return self._roman_to_int(s) > 0

        except Exception as e:
            self.logger.warning(f"Roman check failed for {number}: {e}")
            return False
    
    def _roman_to_int(self, s: str) -> int:
        roman = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }

        total = 0
        prev = 0

        for ch in reversed(s):
            val = roman.get(ch, 0)

            if val < prev:
                total -= val
            else:
                total += val
                prev = val

        return total

    def is_decimal(self, value):
        if re.match(r'\d+[a-zA-Z]*$', value) != None:
            return True
        else:
            return False
    
    def value_type(self, value):
        try:
            isDecimal  = self.is_decimal(value)
            if isDecimal == True:
                return DECIMAL 
            isRoman = self.is_roman(value)
            if isRoman == True:
                return ROMAN 
            elif re.match('[a-z]+$', value) != None:
                return SMALLSTRING
            else:
                return GENSTRING
        except Exception as e:
            self.logger.error(f"Failed to determine value type for {value}: {e}")
            return GENSTRING  # Fallback 
    
    # compares two section numbers and returns 
    # 0 if value1 and value2 are at the same level
    # 1 if value2 is higher in hierarchy that value1
    # -1 if value2 is lower in hierarchy than value1
    # Example: (1,a) = -1
    #          (a,2) = 1
    #          (a,b) = 0 
    def comp_special_nums(self, value1, value2):
        self.logger.debug(f"Checking special comparison: {value1} vs {value2}")
        if value1 == 'i' and value2 == 'j':
            retval = (SMALLSTRING, 0) 
        elif value2 == 'i' and (value1 == 'h' or value1 == 'hh' or value1 == 'ha'):
            retval = (SMALLSTRING, 0) 
        elif value2 == 'x' and value1 == 'w':
            retval = (SMALLSTRING, 0) 
        elif value2 == 'y' and value1 == 'x':
            retval = (SMALLSTRING, 0) 
        elif value2 == 'x' and value1 == 'ix':
            retval = (ROMAN, 0) 
        elif value2 == 'xi' and value1 == 'x':
            retval = (ROMAN, 0) 
        elif value2 == 'v' and value1 == 'u':
            retval = (SMALLSTRING, 0) 
        elif value2 == 'w' and value1 == 'v':
            retval = (SMALLSTRING, 0) 
        else:
            retval = None

        return retval

    def comp_nums(self, depth, value1, value2, valueType1):
        #print 'value1: %s type:%d value2: %s type: %d' % (value1, valueType1, value2, valueType2)
        # handle the special case of i

        self.logger.debug(f"Comparing at depth {depth}: {value1} ({valueType1}) vs {value2}")
        valueType2 = self.value_type(value2)
        if valueType1 == ARTICLE:
            compval = -1
        else:
            retval = self.comp_special_nums(value1, value2)
            if retval != None:
                (valueType2, compval) = retval
            else:
                if valueType1 == None:
                    valueType1 = self.value_type(value1)

                compval    = self.comp_level(depth, value1, value2, valueType1, valueType2)

        i = compval 
        while i < 0:
            self.depthTypes[depth-i] = -1
            self.valnum    [depth-i] = -1
            i += 1
        # store the state
        self.valnum    [depth - compval] = value2
        self.depthTypes[depth - compval] = valueType2
        return (valueType2, compval)
        

    def prev_level_match(self, value, valueType, depth):
        self.logger.debug(f"Searching previous match for: {value} of type {valueType} at depth {depth}")

        matches = []
        for i in range(0, depth):
            if valueType == self.depthTypes[i]:
                matches.append(i)

        if len(matches) <= 0:
            depthmatch = None
        else:
            finalmatch = []
            nextval    = self.nextvals[valueType]
            for match in matches:    
               if self.is_next_val(nextval, self.valnum[match], value):
                  finalmatch.append(match)
            if len(finalmatch) <= 0:
                matches.sort(reverse=True)
                depthmatch = matches[0]
            else:
                finalmatch.sort(reverse=True)
                depthmatch = finalmatch[0]
        if depthmatch == None:
            compval = None
        else:
            compval = depth - depthmatch
        return compval

    def comp_level(self, depth, value1, value2, valueType1, valueType2):
        if valueType1 == valueType2:
            compval =  0
        else:
            # its a new level if it starts with the starting of each type
            if value2 in ['A', '1', 'a']:
                compval = -1
            else:
                compval = self.prev_level_match(value2, valueType2, depth)
                if compval == None: 
                    # move up one level
                    compval = -1

        return compval

class CompareLevelSebi:

    def __init__(self, val=None, depthType=None):

        self.logger = logging.getLogger(__name__)

        self.depthTypes = [depthType, -1, -1, -1, -1, -1]
        self.valnum = [val, None, None, None, None, None]

        self.roman_order = [
            "i", "ii", "iii", "iv", "v",
            "vi", "vii", "viii", "ix", "x",
            "xi", "xii", "xiii", "xiv", "xv",
            "xvi", "xvii", "xviii", "xix", "xx",
            "xxi", "xxii", "xxiii", "xxiv", "xxv",
            "xxvi", "xxvii", "xxviii", "xxix", "xxx"
        ]

        self.roman_index = {
            value: index
            for index, value in enumerate(self.roman_order)
        }

    def _normalize(self, token: str) -> str:

        if token is None:
            return ""

        t = str(token).strip()

        t = re.sub(r'^[\s\(\[]+', '', t)
        t = re.sub(r'[\s\.\)\]\:]+$', '', t)

        return t.strip()

    def is_decimal(self, value: str) -> bool:

        value = self._normalize(value)

        return re.fullmatch(
            r'\d+(?:\.\d+)*',
            value
        ) is not None

    def is_roman(self, value: str) -> bool:

        value = self._normalize(value)

        roman_re = (
            r'^(M{0,4}'
            r'(CM|CD|D?C{0,3})'
            r'(XC|XL|L?X{0,3})'
            r'(IX|IV|V?I{0,3}))$'
        )

        return re.fullmatch(
            roman_re,
            value,
            re.IGNORECASE
        ) is not None

    def is_alpha(self, value: str) -> bool:

        value = self._normalize(value)

        return re.fullmatch(
            r'[A-Za-z]+',
            value
        ) is not None

    def value_type(self, value):

        v = self._normalize(value)

        if self.is_decimal(v):
            return DECIMAL

        if self.is_roman(v):
            return ROMAN

        if self.is_alpha(v):
            return SMALLSTRING

        return GENSTRING

    def resolve_alpha_vs_roman(self, prev, curr):

        prev = self._normalize(prev).lower()
        curr = self._normalize(curr).lower()

        if curr not in self.roman_index:
            return SMALLSTRING

        # multi-char => almost always roman
        if len(curr) > 1:
            return ROMAN

        ambiguous = {"i", "v", "x"}

        if curr not in ambiguous:
            return SMALLSTRING

        # h -> i -> j
        if (
            len(prev) == 1 and
            len(curr) == 1 and
            prev.isalpha()
        ):

            if ord(curr) == ord(prev) + 1:
                return SMALLSTRING

        # roman continuation
        if prev in self.roman_index:

            if (
                self.roman_index[curr]
                ==
                self.roman_index[prev] + 1
            ):
                return ROMAN

        return ROMAN

    def is_same_family(self, v1, v2, t1, t2):

        if t1 != t2:
            return False

        # case-sensitive alpha families
        if t1 == SMALLSTRING:

            if v1.islower() != v2.islower():
                return False

        # case-sensitive roman families
        if t1 == ROMAN:

            if v1.islower() != v2.islower():
                return False

        return True

    def get_decimal_depth(self, token):

        token = self._normalize(token)

        parts = [
            p for p in token.split('.')
            if p.strip()
        ]

        return max(0, len(parts) - 1)

    def comp_nums(self, depth, value1, value2, valueType1):

        try:

            v1 = self._normalize(value1)
            v2 = self._normalize(value2)

            # -----------------------------------------
            # DECIMAL
            # -----------------------------------------

            if self.is_decimal(v2):

                valueType2 = DECIMAL

                new_depth = self.get_decimal_depth(v2)

            # -----------------------------------------
            # ALPHA / ROMAN
            # -----------------------------------------

            elif self.is_alpha(v2) or self.is_roman(v2):

                valueType2 = self.resolve_alpha_vs_roman(
                    v1,
                    v2
                )

                # same family continuation
                if self.is_same_family(
                    v1,
                    v2,
                    valueType1,
                    valueType2
                ):

                    new_depth = depth

                else:

                    # sibling restoration
                    found = False

                    for i in range(depth, -1, -1):

                        prev_type = self.depthTypes[i]
                        prev_val = self.valnum[i]

                        if prev_val is None:
                            continue

                        prev_val = self._normalize(prev_val)

                        if self.is_same_family(
                            prev_val,
                            v2,
                            prev_type,
                            valueType2
                        ):

                            new_depth = i
                            found = True
                            break

                    if not found:
                        new_depth = depth + 1

            # -----------------------------------------
            # FALLBACK
            # -----------------------------------------

            else:

                valueType2 = GENSTRING
                new_depth = depth

            compval = depth - new_depth

            store_index = max(0, new_depth)

            if store_index >= len(self.valnum):
                store_index = len(self.valnum) - 1

            self.valnum[store_index] = v2
            self.depthTypes[store_index] = valueType2

            return valueType2, compval

        except Exception as e:

            self.logger.exception(
                f"comp_nums failed for '{value1}' -> '{value2}': {e}"
            )

            return GENSTRING, 0