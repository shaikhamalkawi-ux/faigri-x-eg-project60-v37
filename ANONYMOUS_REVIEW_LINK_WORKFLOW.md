# Put a verified reviewer-safe link into the journal manuscript

1. Create a **separate** public GitHub repository for Project 60 only.
   Suggested name: `faigri-x-eg-project60-v37`.
2. Upload the contents of this public candidate *after* checking the separate
   project's rights and filenames. Do not upload editor-only declarations,
   manuscript title-page files, private source snapshots or conference files.
3. Verify that the repository has the correct `README.md`, frozen 11+1 case
   input files and reproduction scripts and is accessible signed-out.
4. Visit https://anonymous.4open.science/ and create a **read-only anonymous
   mirror** of that repository. Configure substitutions for username, names,
   affiliations, email addresses and any private identifiers.
5. Open the anonymous URL in a logged-out browser; download a sample CSV and
   inspect rendered files to verify no author identity leaks. PDFs/images are
   not automatically anonymized; these should have been pre-screened.
6. Put the **verified anonymous URL** in the double-anonymized reviewer PDF.
   Put the canonical public GitHub URL into the author-only upload metadata
   and the post-acceptance manuscript. Do not place a personal-account URL
   in the reviewer manuscript.
7. Use `insert_verified_repository_links.py` included in the companion
   submission-link patch ZIP to update and recompile both variants.

Until both URLs have been verified, no claim of a public GitHub deposit should
be made in the journal manuscript.
