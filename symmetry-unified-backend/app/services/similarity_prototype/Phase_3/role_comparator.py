from Phase_2.synonym_matcher import SynonymMatcher
from Phase_3.syntax_parser import SyntaxParser

# Pronouns carry no topic information — matching "it" == "it" across two
# completely unrelated sentences tells us nothing about similarity.
# These are skipped (return None) when found in the subject slot.
_GENERIC_PRONOUNS = frozenset({
    "it", "they", "he", "she", "we", "i", "you",
    "this", "that", "these", "those", "one", "there",
})

class RoleComparator:
    def __init__(self):
        self.parser = SyntaxParser()
        self.matcher = SynonymMatcher()

        #Role weights - how much each role contributes to final score
        #verb and subject matter more for meaning
        self.ROLE_WEIGHTS = {
            "subject": 0.30,
            "verb": 0.30,
            "object": 0.25,
            "prep": 0.10,
            "modifiers": 0.05
        }

        #Known antonym pairs for verbs - if detected, apply penalty to similarity score
        self.KNOWN_ANTONYM_PAIRS = {
        ("increase", "decrease"), ("increase", "reduce"),
        ("rise", "fall"), ("rise", "decline"),
        ("grow", "shrink"), ("expand", "contract"),
        ("improve", "worsen"), ("accelerate", "decelerate"),
        ("enter", "exit"), ("attack", "defend"),
        ("win", "lose"), ("buy", "sell"),
        ("open", "close"), ("start", "stop"),
        ("add", "remove"), ("give", "take"),
        ("push", "pull"), ("love", "hate"),
        }


        #penalty applied when verb roles are antonyms
        self.ANTONYM_VERB_PENALTY = 0.2
    

    def is_known_antonym(self, word_a, word_b):
        pair1 = (word_a, word_b)
        pair2 = (word_b, word_a)
        return pair1 in self.KNOWN_ANTONYM_PAIRS or pair2 in self.KNOWN_ANTONYM_PAIRS


    #step 1: compare two individual role values
    def compare_role(self, value_a, value_b, role_name):

        #Both missing -> neutral, don't penalize
        if value_a is None and value_b is None:
            return None

        #One missing -> partial mismatch
        if value_a is None or value_b is None:
            return 0.1

        # Pronoun subjects carry no topic information — skip so they don't
        # inflate the score when two unrelated sentences both open with "it"
        if role_name == "subject":
            if value_a.lower() in _GENERIC_PRONOUNS or value_b.lower() in _GENERIC_PRONOUNS:
                return None

        #exact match
        if value_a == value_b:
            return 1.0

        #use phase 2 Wordnet for semantic similarity
        score = self.matcher.wu_palmer_similarity(value_a, value_b)

        # Strict synset check for SUBJECT
        # Subjects are actors - unrelated subjects = unrelated sentences
        if role_name == "subject":
            if not self.matcher.share_synset(value_a, value_b) and score < 0.9:
                score = 0.0

        # Strict threshold for VERB — only count clear synonym/antonym pairs.
        # Raw Wu-Palmer leaks through for words that share only a distant
        # hypernym (e.g. "keep" vs "apply" both trace back to "act").
        if role_name == "verb":
            if self.matcher.are_direct_antonyms(value_a, value_b) or self.is_known_antonym(value_a, value_b):
                score -= self.ANTONYM_VERB_PENALTY
            elif not self.matcher.share_synset(value_a, value_b) and score < 0.85:
                score = 0.0

        # Strict threshold for OBJECT — same reasoning as verb
        if role_name == "object":
            if not self.matcher.share_synset(value_a, value_b) and score < 0.75:
                score = 0.0

        return score
    
    #step 2: compare modifier lists
    def compare_modifiers(self, mods_a, mods_b):
        if not mods_a and not mods_b:
            return None # both emtpy -> neutral
        
        if not mods_a or not mods_b:
            return 0.3 # one empty -> partial mismatch
        
        #match each modifier in A to best in B
        total_score = 0.0
        for mod_a in mods_a:
            best = max((self.matcher.wu_palmer_similarity(mod_a, mod_b) for mod_b in mods_b), default=0.0)
            total_score += best
        return round(total_score / len(mods_a), 4)
    
    #step 3: compare all roles and compute weighted scores
    def compare_roles(self, roles_a, roles_b):
        # print(f"\n  Role comparison:")

        role_scores = {}
        total_weight = 0.0
        weighted_sum = 0.0

        #compare each scalar role
        for role in ["subject", "verb", "object", "prep"]:
            score = self.compare_role(roles_a.get(role), roles_b.get(role), role)

            if score is None:
                # print(f"    {role:<10}: both missing → skipped")
                continue

            weight = self.ROLE_WEIGHTS[role]
            role_scores[role] = score
            weighted_sum += score * weight
            total_weight += weight

            # print(f"    {role:<10}: '{roles_a.get(role)}' vs '{roles_b.get(role)}' → {score:.4f} (weight {weight})")

        #compare modifiers
        mod_score = self.compare_modifiers(roles_a.get("modifiers", []), roles_b.get("modifiers", []))

        if mod_score is not None:
            weight = self.ROLE_WEIGHTS["modifiers"]
            role_scores["modifiers"] = mod_score
            weighted_sum += mod_score * weight
            total_weight += weight

            # print(f"    {'modifiers':<10}: {roles_a.get('modifiers')} vs {roles_b.get('modifiers')} → {mod_score:.4f} (weight {weight})")

        #normalize by actual weights used (handle missing roles)
        final_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
        return final_score
    
    #step 4: main compare function
    def compare(self, sentence_a, sentence_b):
        roles_a = self.parser.extract_roles(sentence_a)
        roles_b = self.parser.extract_roles(sentence_b)

        # print(f"\n  Roles A: {roles_a}")
        # print(f"  Roles B: {roles_b}")

        score = self.compare_roles(roles_a, roles_b)
        return score
    
#testing
if __name__ == "__main__":
    comparator = RoleComparator()

    pairs = [
        ("The cat sat on the mat",          "A feline rested on a rug"),
        ("The cat sat on the mat",          "Stock markets crashed today"),
        ("The company increased revenue",   "The company reduced revenue"),
        ("I created a robot",               "I built a robot"),
        ("I wrote the letter",              "The letter was written by me"),
        ("The manager announced the policy during the meeting",
         "During the meeting the manager announced the policy"),
    ]

    print("=" * 70)
    for sentence_a, sentence_b in pairs:
        print(f"\nSentence A: {sentence_a}")
        print(f"Sentence B: {sentence_b}")
        score = comparator.compare(sentence_a, sentence_b)
        print(f"Phase 3 Score: {score}")
        print("-" * 70)


