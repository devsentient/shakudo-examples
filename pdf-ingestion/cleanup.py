import os

def cleanup_md(pdf_dir, md_dir):
    """
    Loops over all PDF files in `pdf_dir`, extracts text and images,
    then writes the results to a single Markdown file `md_file_name`.
    """
    # Open the output markdown file in write mode

    # Loop over everything in the pdf_dir
    for file_name in os.listdir(pdf_dir):
        if file_name.lower().endswith(".md"):
            md_file_lns = open(os.path.join(pdf_dir, file_name)).readlines()
            new_lns = [ln.replace('```markdown', "").replace("```", '\n') for ln in md_file_lns]
            for ln in new_lns:
                if '```' in ln:
                    print(ln)
            newfile = os.path.join(md_dir, file_name)
            with open(newfile, 'w') as f:
                for ln in new_lns:
                    f.write(ln)

cleanup_md('./pdf_output', './cleanned_md')
