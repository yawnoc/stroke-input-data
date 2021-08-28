#!/usr/bin/env python3

"""
# generate.py

Parse `codepoint-character-sequence.txt` and `ranking.txt`,
generating `sequence-exact-characters.txt`
and `sequence-prefix-characters.txt`.

Licensed under "MIT No Attribution" (MIT-0),
see <https://spdx.org/licenses/MIT-0>.
"""


import itertools
import re


def get_lines(file_name):
  """
  Get the lines in a file.
  """
  
  with open(file_name, 'r', encoding='utf-8') as file:
    return file.read().splitlines()


def join_sorted(string_set, sorting_function):
  """
  Join a set of strings with sorting.
  """
  
  return ''.join(sorted(string_set, key=sorting_function))


CAPTURE_GROUP_REGEX = r'''
  \(
    (?P<alternatives> [1-5|]* )
  \)
'''


def replace_capture_group(group_match_object, group_alternatives_set_list):
  """
  Replace a capture group match object with a back reference.
  Appends the capture group's alternatives (as a set)
  to the supplied list of sets of capture group alternatives.
  """
  
  group_alternatives_string = group_match_object.group('alternatives')
  group_alternatives_set = set(group_alternatives_string.split('|'))
  group_alternatives_set_list.append(group_alternatives_set)
  
  group_index = len(group_alternatives_set_list)
  back_reference = fr'\{group_index}'
  
  return back_reference


BACK_REFERENCE_REGEX = r'''
  \\
  (?P<group_index> [1-9] )
'''


def replace_back_reference(
  back_reference_match_object,
  alternatives_combination
):
  """
  Replace a back reference with the appropriate alternative.
  """
  
  group_index = int(back_reference_match_object.group('group_index'))
  alternative = alternatives_combination[group_index - 1]
  
  return alternative


def to_sequence_set(sequence_regex):
  """
  Convert stroke sequence regex to a stroke sequence set.
  Assumes capture groups:
    1. number at most 9,
    2. are not nested,
    3. contain pure digits separated by pipes, and
    4. are referred to by a backslash followed by
       a positive decimal digit.
  """
  
  group_alternatives_set_list = []
  
  back_referenced_sequence_regex = re.sub(
    CAPTURE_GROUP_REGEX,
    lambda x: replace_capture_group(x, group_alternatives_set_list),
    sequence_regex,
    flags=re.VERBOSE
  )
  
  sequence_set = set()
  
  alternatives_combinations = itertools.product(*group_alternatives_set_list)
  
  for alternatives_combination in alternatives_combinations:
    
    sequence = re.sub(
      BACK_REFERENCE_REGEX,
      lambda x: replace_back_reference(x, alternatives_combination),
      back_referenced_sequence_regex,
      flags=re.VERBOSE
    )
    
    sequence_set.add(sequence)
  
  return sequence_set


class CharactersData:
  """
  Class for characters data.
  """
  
  def __init__(self):
    self.goodly_set = set()
    self.abomination_set = set()
  
  def add_goodly(self, character):
    self.goodly_set.add(character)
  
  def add_abomination(self, character):
    self.abomination_set.add(character)
  
  def add_data(self, characters_data):
    for character in characters_data.goodly_set:
      self.add_goodly(character)
    for character in characters_data.abomination_set:
      self.add_abomination(character)
  
  def to_string(self, sorting_function, max_candidate_count=0):
    goodly_string = join_sorted(self.goodly_set, sorting_function)
    abomination_string = join_sorted(self.abomination_set, sorting_function)
    if max_candidate_count > 0:
      max_abomination_count = max(0, max_candidate_count - len(goodly_string))
      goodly_string = goodly_string[: max_candidate_count]
      abomination_string = abomination_string[: max_abomination_count]
    if len(abomination_string) == 0:
      return goodly_string
    else:
      return f'{goodly_string},{abomination_string}'


IGNORED_RANKING_LINE_REGEX = r'''
  [\s]* [#] .*
'''


COMPLIANT_LINE_REGEX = r'''
  U[+][0-9A-F]{4,5}
    \t
  (?P<character> \S )
  (?P<abomination_asterisk> [*]? )
    \t
  (?P<sequence_regex> [1-5|()\\]+ )
'''


SEQUENCE_EXACT_CHARACTERS_FILE_HEADER = (
'''\
# # sequence-exact-characters.txt

# Character data for exact-match candidates.

# Copyright 2021 Conway.
# Licensed under Creative Commons Attribution 4.0 International (CC-BY-4.0),
# see <https://creativecommons.org/licenses/by/4.0/>.

# Contains tab-separated (stroke sequence, exact-match characters data) pairs,
# where exact-match characters data consists of
# comma-separated (goodly characters, abominable characters) pairs.

# This file is automatically generated by running `generate.py`
# in <https://github.com/stroke-input/stroke-input-data>.
# It should NOT be edited manually.
# Manual edits should be made to `codepoint-character-sequence.txt`.

'''
)


SEQUENCE_PREFIX_CHARACTERS_FILE_HEADER = (
'''\
# # sequence-prefix-characters.txt

# Character data for prefix-match candidates,
# pre-computed for stroke sequences up to length n = {length},
# which limits the live lookup size to ~{rows} rows / 5^(n+1) = {result}.

# Copyright 2021 Conway.
# Licensed under Creative Commons Attribution 4.0 International (CC-BY-4.0),
# see <https://creativecommons.org/licenses/by/4.0/>.

# Contains tab-separated (stroke sequence, prefix-match characters data) pairs,
# where prefix-match characters data consists of
# comma-separated (goodly characters, abominable characters) pairs.

# This file is automatically generated by running `generate.py`
# in <https://github.com/stroke-input/stroke-input-data>.
# It should NOT be edited manually.
# Manual edits should be made to `codepoint-character-sequence.txt`.

'''
)


MAX_CHARACTER = chr(0x10FFFF)
PRECOMPUTE_PREFIX_MATCHES_MAX_STOKE_COUNT = 3
MAX_PREFIX_MATCH_COUNT = 20
FULL_LOOKUP_ROW_COUNT = 30e3


if __name__ == '__main__':
  
  sorting_rank_from_character = {}
  exact_characters_data_from_sequence = {}
  
  with open('.ignored-lines.txt', 'w', encoding='utf-8') \
  as ignored_lines_file:
    
    infinite_sorting_rank = 0
    for line_number, ranking_line in enumerate(get_lines('ranking.txt'), 1):
      
      line_match_object = re.fullmatch(
        IGNORED_RANKING_LINE_REGEX,
        ranking_line,
        flags=re.VERBOSE
      )
      line_is_ignored = line_match_object is not None
      
      if line_is_ignored:
        ignored_lines_file.write(ranking_line + '\n')
        continue
      
      for character in ranking_line:
        if character not in sorting_rank_from_character:
          sorting_rank_from_character[character] = line_number
          infinite_sorting_rank = line_number + 1
    
    def character_sorting_function(character):
      
      sorting_rank = \
        sorting_rank_from_character.get(character, infinite_sorting_rank)
      
      return (sorting_rank, character)
    
    for codepoint_character_sequence_line \
    in get_lines('codepoint-character-sequence.txt'):
      
      line_match_object = re.fullmatch(
        COMPLIANT_LINE_REGEX,
        codepoint_character_sequence_line,
        flags=re.VERBOSE
      )
      line_is_not_compliant = line_match_object is None
      
      if line_is_not_compliant:
        ignored_lines_file.write(codepoint_character_sequence_line + '\n')
        continue
      
      character = line_match_object.group('character')
      abomination_asterisk = line_match_object.group('abomination_asterisk')
      sequence_regex = line_match_object.group('sequence_regex')
      
      is_abomination = len(abomination_asterisk) > 0
      sequence_set = to_sequence_set(sequence_regex)
      
      for sequence in sequence_set:
        
        try:
          exact_characters_data = exact_characters_data_from_sequence[sequence]
        except KeyError:
          exact_characters_data = \
            exact_characters_data_from_sequence[sequence] = CharactersData()
        
        if is_abomination:
          exact_characters_data.add_abomination(character)
        else:
          exact_characters_data.add_goodly(character)
  
  sorted_sequences = sorted(exact_characters_data_from_sequence.keys())
  
  with open('sequence-exact-characters.txt', 'w', encoding='utf-8') \
  as sequence_exact_characters_file:
    
    sequence_exact_characters_file.write(SEQUENCE_EXACT_CHARACTERS_FILE_HEADER)
    
    for sequence in sorted_sequences:
      
      exact_characters_data = exact_characters_data_from_sequence[sequence]
      exact_characters_data_string = \
        exact_characters_data.to_string(character_sorting_function)
      sequence_exact_characters_line = \
        f'{sequence}\t{exact_characters_data_string}'
      sequence_exact_characters_file\
        .write(sequence_exact_characters_line + '\n')
  
  prefix_sequence_list = [
    ''.join(stroke_digit_combination)
      for length in range(1, 1 + PRECOMPUTE_PREFIX_MATCHES_MAX_STOKE_COUNT)
      for stroke_digit_combination in itertools.product('12345', repeat=length)
  ]
  
  with open('sequence-prefix-characters.txt', 'w', encoding='utf-8') \
  as sequence_prefix_characters_file:
    
    sequence_prefix_characters_file\
      .write(
        SEQUENCE_PREFIX_CHARACTERS_FILE_HEADER
          .format(
            length=PRECOMPUTE_PREFIX_MATCHES_MAX_STOKE_COUNT,
            rows=int(FULL_LOOKUP_ROW_COUNT),
            result=int(
              FULL_LOOKUP_ROW_COUNT
              / pow(5, PRECOMPUTE_PREFIX_MATCHES_MAX_STOKE_COUNT + 1),
            )
          )
      )
    
    for prefix_sequence in prefix_sequence_list:
      
      prefix_characters_data = CharactersData()
      
      for full_sequence in exact_characters_data_from_sequence:
        if prefix_sequence < full_sequence < prefix_sequence + MAX_CHARACTER:
          exact_characters_data = \
            exact_characters_data_from_sequence[full_sequence]
          prefix_characters_data.add_data(exact_characters_data)
      
      prefix_characters_data_string = \
        prefix_characters_data\
          .to_string(character_sorting_function, MAX_PREFIX_MATCH_COUNT)
      sequence_prefix_characters_line = \
        f'{prefix_sequence}\t{prefix_characters_data_string}'
      sequence_prefix_characters_file\
        .write(sequence_prefix_characters_line + '\n')
