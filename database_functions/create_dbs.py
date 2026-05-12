from database_functions.client_db import create_table
from database_functions.ration_db import create_ration_table
from database_functions.links_db import create_table_links
from database_functions.admin_db import create_admins_table, init_superadmin
from config import administrators


def create_dbs():
    create_table()
    create_ration_table()
    create_table_links()
    create_admins_table()
    
    if administrators:
        superadmin_id = administrators[0]
        init_superadmin(superadmin_id)

