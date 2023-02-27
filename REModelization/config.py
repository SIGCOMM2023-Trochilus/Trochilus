#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging
class MyLogging:
    def __init__(self) -> None:
        self.logPath = '../data/log/'
        self.logName = 'RE2DFA.log'
        self.logFile = self.logPath + self.logName
        # format of output
        logging.basicConfig(
            level=logging.DEBUG, # CRITICAL > ERROR > WARNING > INFO > DEBUG，default: WARNING
            # format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s:  %(message)s',
            format='%(asctime)s %(levelname)s:  %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            filename=self.logFile,
            filemode='a'
        )

        
    
    @staticmethod
    def debug_logger(content):
        logging.debug(content)
    
    @staticmethod
    def info_logger(content):
        logging.info(content)

    @staticmethod
    def warning_logger(content):
        logging.warning(content)

    @staticmethod
    def error_logger(content):
        logging.error(content)
