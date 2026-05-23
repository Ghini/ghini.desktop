from bauble.plugins.garden.accession_editor import (
    _source_exact_text_match,
    _source_matches_text,
    _unique_source_contacts,
)


class ContactStub:
    def __init__(self, name, id=None):
        self.name = name
        self.id = id

    def __str__(self):
        return "" if self.name is None else self.name


def test_source_contacts_are_sorted_and_deduplicated_for_combo_display():
    contacts = [
        ContactStub("Zulu Nursery", id=3),
        ContactStub("alpha nursery", id=2),
        ContactStub("Alpha Nursery", id=1),
        ContactStub("", id=4),
        ContactStub(None, id=5),
        ContactStub("Beta Nursery", id=6),
    ]

    assert [str(contact) for contact in _unique_source_contacts(contacts)] == [
        "Alpha Nursery",
        "Beta Nursery",
        "Zulu Nursery",
    ]


def test_source_completion_matches_case_insensitive_substrings_and_ids():
    contact = ContactStub("Daily Workflow Nursery", id=42)

    assert _source_matches_text(contact, "daily")
    assert _source_matches_text(contact, "workflow")
    assert _source_matches_text(contact, "NURS")
    assert _source_matches_text(contact, "4")
    assert not _source_matches_text(contact, "missing")


def test_source_exact_match_accepts_display_text_or_id():
    contact = ContactStub("Daily Workflow Nursery", id=42)

    assert _source_exact_text_match(contact, "daily workflow nursery")
    assert _source_exact_text_match(contact, "42")
    assert not _source_exact_text_match(contact, "daily")
