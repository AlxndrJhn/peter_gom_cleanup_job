import datetime
import logging
import logging.handlers
import pathlib
import traceback
from collections import defaultdict

import gom


# Variables
ROOT = R"C:\Result\alex_test_cleanup"
log_filename = "C:/Result/logs/scheduled_cleanup.log"


# logger

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
pathlib.Path(log_filename).parent.mkdir(parents=True, exist_ok=True)
max_bytes = 1024 * 1024  # 1MB
backup_count = 30  # keep 30 old log files
file_handler = logging.handlers.RotatingFileHandler(
    log_filename, maxBytes=max_bytes, backupCount=backup_count
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def show_error_popup(errors: str):
    logger.error(f"Error in cleanup job: {errors}")
    gom.script.sys.execute_user_defined_dialog(
        content="""<dialog>
        <title>Error in cleanup</title>
        <style></style>
        <control id="Close"/>
        <position>automatic</position>
        <embedding>always_toplevel</embedding>
        <sizemode>automatic</sizemode>
        <size width="255" height="169"/>
        <content rows="1" columns="2">
        <widget rowspan="1" column="0" columnspan="1" type="image" row="0">
        <name>image</name>
        <tooltip></tooltip>
        <use_system_image>true</use_system_image>
        <system_image>system_message_critical</system_image>
        <data><![CDATA[AAAAAAAAAA==]]></data>
        <file_name></file_name>
        <keep_original_size>true</keep_original_size>
        <keep_aspect>true</keep_aspect>
        <width>0</width>
        <height>0</height>
        </widget>
        <widget rowspan="1" column="1" columnspan="1" type="display::text" row="0">
        <name>text</name>
        <tooltip></tooltip>
        <text>&lt;!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
        &lt;html>&lt;head>&lt;meta name="qrichtext" content="1" />&lt;style type="text/css">
        p, li { white-space: pre-wrap; }
        &lt;/style>&lt;/head>&lt;body style="    ">
        &lt;p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Issue with cleanup&lt;/p>&lt;/body>&lt;/html></text>
        <wordwrap>false</wordwrap>
        </widget>
        </content>
        </dialog>"""
    )


def main():
    root_path = pathlib.Path(ROOT)

    all_folders = [pathlib.Path(p) for p in root_path.glob("*")]
    logger.info(f"Found {len(all_folders)} folders in {root_path}")

    TYPES = ["SGT5-4000F"]
    CAST_MACHINED = [" CAST ", " MACHINED "]

    all_folders = [
        folder
        for folder in all_folders
        if any(t.lower() in folder.name.lower() for t in TYPES)
        and any(c.lower() in folder.name.lower() for c in CAST_MACHINED)
    ]
    logger.info(
        f"Found {len(all_folders)} folders with type and cast/machined in {root_path}"
    )

    error_collector_per_folder = defaultdict(list)
    for folder in all_folders:
        logger.info(f"Processing folder `{folder}`")
        all_atos_files = list(folder.glob("*.atos"))
        logger.info(f"  {len(all_atos_files)} atos files in `{folder}`")
        min_age = 14  # days
        now = datetime.datetime.now()
        all_old_atos_files = [
            f
            for f in all_atos_files
            if (now - datetime.datetime.fromtimestamp(f.stat().st_mtime)).days > min_age
        ]
        logger.info(f"  {len(all_old_atos_files)} old atos files in `{folder}`")
        for atos_file in all_old_atos_files:
            try:
                file_size_mb = atos_file.stat().st_size / 1024 / 1024
                # step 1: open in GOM inspect
                gom.script.sys.load_project(file=str(atos_file))

                # step 2: reduce project size
                logger.info(
                    f"Reducing project size of `{folder}` ({file_size_mb:.2f}MB)"
                )
                gom.script.atos.remove_measuring_data_from_project(
                    remove_data="remove_all_data"
                )
                gom.script.sys.save_project()
                file_size_mb = atos_file.stat().st_size / 1024 / 1024
                logger.info(f"Finished cleanup of `{folder}` ({file_size_mb:.2f}MB)")
            except Exception as e:
                stacktrace = "\n".join(
                    [
                        f"  {line}"
                        for line in traceback.format_exception(
                            type(e), e, e.__traceback__
                        )
                    ]
                )
                err = f"Error in cleanup job of `{folder}`: {e}\n{stacktrace}"
                error_collector_per_folder[folder].append(err)
                logger.error(err)

            try:
                logger.info(f"Closing `{folder}`")
                # gom.script.sys.close_project()
            except Exception:
                pass

    if any(error_collector_per_folder.values()):
        err_msg = "\n".join(
            [
                f"`{folder}`:\n{errors}"
                for folder, errors in error_collector_per_folder.items()
            ]
        )
        show_error_popup(err_msg)


if __name__ == "__main__":
    main()
