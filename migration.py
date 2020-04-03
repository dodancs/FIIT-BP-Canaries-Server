import sys
import uuid
import datetime

if len(sys.argv) < 2:
    print('Provide file path & output file path')
    exit(1)


print(sys.argv[1])


def site(name):
    if name == "reddit.com":
        return "'620247b1-5706-43de-92ef-a8596ab85955'"
    if name == "stackoverflow.com":
        return "'98c700c6-b031-4b0a-8f51-90049fd23983'"
    if name == "netflix.com":
        return "'90ef499a-7588-46c0-9a24-16f6b7210a2f'"
    if name == "wikipedia.org":
        return "'459e6816-c6ce-4b59-9c75-55c6f0608694'"
    if name == "sme.sk":
        return "'fb7e0cb2-a2f9-40e8-b70a-769cd31cd29c'"
    if name == "wordpress.com":
        return "'d43c3a7f-a1f3-494f-b88f-75c70a17f3b8'"
    if name == "aktuality.sk":
        return "'cea3af80-22a9-480a-b2e5-ed0e6099cc04'"
    if name == "heureka.sk":
        return "'e8ade6f4-f0e2-4bfb-8b3c-664cf149daf2'"
    if name == "github.com":
        return "'c6ce09e2-f57b-4440-baa8-6d31d698f180'"
    if name == "hnonline.sk":
        return "'127c6c31-abd9-44f4-8f4f-ef9d563e6a5a'"
    if name == "emefka.sk":
        return "'d90e0aad-4a3a-4e60-a7d8-509c0b69878d'"
    if name == "dropbox.com":
        return "'9a98f363-6e88-485d-bce4-2965dae7f09c'"
    if name == "patreon.com":
        return "'2003ad0c-fe64-43fc-84f3-3b82d5ac7bb3'"
    if name == "skype.com":
        return "'e7ff2d7e-3610-4960-8dc3-69cb8bb3fb37'"
    if name == "wish.com":
        return "'9f6837c0-5317-4f87-afb7-b64a14ec8324'"
    if name == "mega.nz":
        return "'e44a89f4-f602-42cc-b8ae-9c7723805831'"
    if name == "pinterest.com":
        return "'37f3de22-5aa3-4d77-87bb-589151285bb5'"
    if name == "twitter.com":
        return "'33fc60e7-060c-41af-92ae-efd3c1b6c670'"
    if name == "quora.com":
        return "'ef49833d-bf6e-410f-9143-67395a59262c'"
    if name == "tumblr.com":
        return "'79859003-4545-4d05-a118-aee5bfd146b7'"

    return "NULL"


with open('output.sql', 'w', encoding='utf-8') as output:

    output.write(
        'insert into `canaries` (`uuid`, `domain`, `site`, `testing`, `setup`, `email`, `password`, `data`, `created_at`, `updated_at`) values\n')

    with open(sys.argv[1], encoding='utf-8') as export:
        for line in export:
            split = line.split('|')
            output.write("('%s', '%s', %s, '%s', '%s', '%s', '%s', '%s', %s, %s),\n" %
                         (
                             uuid.uuid4(),
                             "a10bbc2b-baa3-4106-b883-4ef9b4fe19d6" if split[2].strip(
                             ) == "1" else "998e5e31-553e-4d55-8aeb-cc713a69a3f7",
                             site(split[5].strip()),
                             "0",
                             split[10].strip(),
                             split[4].strip(),
                             split[6].strip(),
                             '{"username": "' + (split[4].strip().split('@')[0]) +
                             '"}' if split[10].strip() == "0" else '{"username": "' + (split[4].strip().split('@')[0]) +
                             '", "firstname": "' +
                             split[7].strip() + '", "lastname": "' +
                             split[8].strip() + '", "birthday": "' +
                             split[9].strip() + '"}',
                             'CURRENT_TIMESTAMP',
                             'CURRENT_TIMESTAMP'
                         )
                         )
        export.close()
