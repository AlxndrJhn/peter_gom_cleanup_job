import datetime
import logging
import logging.handlers
import pathlib
import traceback
from collections import defaultdict

import gom

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
log_filename = "scheduled_cleanup.log"
max_bytes = 1024 * 1024  # 1MB
backup_count = 30  # keep 30 old log files
file_handler = logging.handlers.RotatingFileHandler(
    log_filename, maxBytes=max_bytes, backupCount=backup_count
)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def show_error_popup(e: Exception):
    stacktrace = "\n".join(
        [
            f"  {line}"
            for line in traceback.format_exception(type(e), e, e.__traceback__)
        ]
    )
    logger.error(f"Error in cleanup job: {e}\n{stacktrace}")
    gom.script.sys.execute_user_defined_dialog(
        content="<dialog>"
        " <title>Error in cleanup job</title>"
        " <style></style>"
        ' <control id="Ok"/>'
        " <position></position>"
        " <embedding></embedding>"
        " <sizemode></sizemode>"
        ' <size width="271" height="172"/>'
        ' <content columns="1" rows="3">'
        '  <widget column="0" type="label" row="0" rowspan="1" columnspan="1">'
        "   <name>label</name>"
        "   <tooltip></tooltip>"
        f"   <text>{e}{stacktrace}</text>"
        "   <word_wrap>true</word_wrap>"
        "  </widget>"
        " </content>"
        "</dialog>"
    )


def main():
    root_path = pathlib.Path(R"C:\Result")

    all_folders = [pathlib.Path(p) for p in root_path.glob("*")]
    logger.info(f"Found {len(all_folders)} folders in {root_path}")

    TYPES = ["SGT-5000"]
    CAST_MACHINED = [" CAST ", " MACHINED "]

    all_folders = [
        folder
        for folder in all_folders
        if any(t in folder.name for t in TYPES)
        and any(c in folder.name for c in CAST_MACHINED)
    ]
    logger.info(
        f"Found {len(all_folders)} folders with type and cast/machined in {root_path}"
    )

    error_collector_per_folder = defaultdict(list)
    for folder in all_folders:
        logger.info(f"Processing folder {folder}")
        all_atos_files = list(folder.glob("*.atos"))
        min_age = datetime.timedelta(days=14)
        all_old_atos_files = [
            f
            for f in all_atos_files
            if datetime.datetime.now() - f.stat().st_mtime > min_age
        ]
        for atos_file in all_old_atos_files:
            try:
                # step 1: open in GOM inspect
                gom.script.sys.load_project(str(atos_file))

                # step 2: reduce project size
                logger.info(f"Reducing project size of {folder}")
                gom.script.sys.remove_data(remove_data="remove_all_data")
                gom.script.sys.save_project()
                logger.info(f"Finished cleanup of {folder}")
            except Exception as e:
                stacktrace = "\n".join(
                    [
                        f"  {line}"
                        for line in traceback.format_exception(
                            type(e), e, e.__traceback__
                        )
                    ]
                )
                err = f"Error in cleanup job of {folder}: {e}\n{stacktrace}"
                error_collector_per_folder[folder].append(err)
                logger.error(err)

            try:
                logger.info(f"Closing {folder}")
                gom.script.sys.close_project()
            except Exception:
                pass

    if any(error_collector_per_folder.values()):
        raise show_error_popup(
            "\n".join(
                [
                    f"{folder}:\n{error}"
                    for folder, errors in error_collector_per_folder.items()
                    for error in errors
                ]
            )
        )


if __name__ == "__main__":
    main()
