from src.exception import CustomException
from src.logger import logging
from src.constant.training_pipeline import SCHEMA_FILE_PATH
from src.entity.artifact_entity import DataIngestionArtifact, DataValidationArtifact
from src.entity.config_entity import DataValidationConfig
import os, sys
from src.utils.utilis import read_yaml_file, write_yaml_file
from scipy.stats import ks_2samp
import pandas as pd
from pandas import DataFrame

class DataValidation:
    
    def __init__(self, data_ingestion_artifact: DataIngestionArtifact, 
                 data_validation_config:DataValidationConfig):
        try:
            self.data_ingestion_artifact =data_ingestion_artifact
            self.data_validation_config = data_validation_config
            self._schema_config = read_yaml_file(SCHEMA_FILE_PATH)
        except Exception as e:
            raise CustomException(e, sys)
        


    def validate_number_of_columns(self,dataframe:pd.DataFrame)->bool:
            try:
                number_of_columns = len(self._schema_config["columns"])
                logging.info(f"Required number of columns: {number_of_columns}")
                logging.info(f"Data frame has columns: {len(dataframe.columns)}")
                if len(dataframe.columns)==number_of_columns:
                    return True
                return False
            except Exception as e:
                raise CustomException(e,sys)


    def is_numeric_column_exist(self, dataframe : DataFrame)->bool:
        try:
            numerical_columns = self._schema_config["numerical_columns"]
            dataframe_columns = dataframe.columns

            missing_numerical_columns = []
            numerical_columns_present = True
            for num_column in numerical_columns:
                if num_column not in dataframe_columns:
                    numerical_columns_present = False
                    missing_numerical_columns.append(num_column)
            logging.info(f"Missing Numerical Columns : {missing_numerical_columns}")
            return numerical_columns_present


        except Exception as e:
            raise CustomException(e, sys)


    @staticmethod
    def read_data(file_path)->DataFrame:
        try:
            return pd.read_csv(file_path)

        except Exception as e:
            raise CustomException(e, sys)

    def detect_dataset_drift(self, base_df, current_df, threshold:float=0.05)->bool:
        try:
            status=True
            report ={}
            for column in base_df.columns:
                d1 = base_df[column]
                d2 = current_df[column]
                is_same_dist = ks_2samp(d1,d2)
                if  threshold<=is_same_dist.pvalue:
                    is_found = False
                else:
                    is_found = True
                    status = False
                report.update(
                    {
                        column: {
                            "p_value":float(is_same_dist.pvalue),
                            "drift_status":is_found
                        }
                    }
                )


            drift_report_file_path = self.data_validation_config.drift_report_file_path
                
                #create directory 
            dir_path = os.path.dirname(drift_report_file_path)
                
            os.makedirs(dir_path, exist_ok=True)
            write_yaml_file(file_path=drift_report_file_path, content=report)
            return status
        except Exception as e:
            raise CustomException(e,sys)




    def initiate_data_validation(self) -> DataValidationArtifact:
        try: 
            error_message = ""
            train_file_path = self.data_ingestion_artifact.trained_file_path
            test_file_path = self.data_ingestion_artifact.test_file_path

            # Reading Train and Test file as Data Frame
            train_dataframe = DataValidation.read_data(train_file_path)
            test_dataframe = DataValidation.read_data(test_file_path)

            # Validate Number of Columns
            status = self.validate_number_of_columns(dataframe=train_dataframe)
            if not status:
                error_message = f"{error_message}Train dataframe does not contain all columns. \n"

            status = self.validate_number_of_columns(dataframe=test_dataframe)
            if not status:
                error_message = f"{error_message}Test dataframe does not contain all the columns. \n"

            # Validate Numerical Columns
            status = self.is_numeric_column_exist(dataframe=train_dataframe)
            if not status:
                error_message = f"{error_message}Numerical Columns are missing from Train DataFrame"

            status = self.is_numeric_column_exist(dataframe=test_dataframe)
            if not status:
                error_message = f"{error_message}Numerical Columns are missing from Test DataFrame"
            
            if len(error_message)>0:
                raise Exception(error_message)
            
            # Let's check data drift
            status = self.detect_dataset_drift(base_df=train_dataframe, current_df=test_dataframe)

            data_validation_artifact = DataValidationArtifact(
                validaion_status= status,
                valid_train_file_path=self.data_ingestion_artifact.trained_file_path,
                valid_test_file_path= self.data_ingestion_artifact.test_file_path,
                invalid_test_file_path= None,
                invalid_train_file_path=None,
                drift_report_file_path=self.data_validation_config.drift_report_file_path
            )
            
            logging.info(f"Data Validation Artifact : {data_validation_artifact}")
            return data_validation_artifact
        except Exception as e:
            raise CustomException(e, sys)