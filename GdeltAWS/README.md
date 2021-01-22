# Projet NoSQL 728 - GDELT database

## First step
Dowload 
* [Ansible name](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html): 2.9.15
* [AWS cli name](https://example.com): Version 2
*
           
       pip install boto3
## Second step

Go to your terminal and do :

        vim ~/.aws/credentials
        
 And copy/paste your credentials from your **Accounts Details**

## Third step
1. Now go to AWS console in EC2 section :

    - create your KeyPair and named it : **gdeltKeyPair** 

    - OR load the **gdeltKeyPair.pem** in secrets folder.

2. It will donwload it into your Downloads folder, you can copy/paste it to secrets project folder (the gdeltKeyPair.pem key)

3. Now you can go to project folder and run command :

       python script/AWS_cli.py --help
        
 It will show you all the command line you can do with the python interface script.
 
 For example :
 
       python script/AWS_cli.py --create_cluster spark 2 m5.xlarge
       python script/AWS_cli.py --create_cluster cassandra 2 m5.xlarge 
       python script/AWS_cli.py --create_bucket bucket_name
       python script/AWS_cli.py --upload_bucket masterfilelist.txt bucket_name
       python script/AWS_cli.py --deploy_db 5 cassandra
       
       there are others command like see all instances and create a config file with it.
       add volume in an instance
   
 The first will create the spark cluster with 2 instances (one master / one slave) and m5.xlarge instance type
 The second is the same but for the db cluster (choose between cassandra / mongodb / neo4j)
 The third and fourth are for creating the S3 bucket and upload any file you want (with the path file + filename and the S3 bucket name created)
 Finally you can deploy db with docker by selecting the number of nodes and the type
 
 ## Fourth step
 
 To use Zepellin in the spark cluster, you must allow ssh connection :
 
 1. go to the EMR spark cluster
 2. click on *Edit inbound rules* in **Security groups to Master**
 3. Add SSH rule if doesn't exist from Anywhere 
 4. go to secrets folder with gdeltKeyPair.pem key and do
 
        ssh -L 8892:127.0.0.1:8890 -i gdeltKeyPair.pem hadoop@ec2-[name of your EC2 instance spark master]
        
 5. Now you can change the interpreter parameter in Zepelin in Spark session and modify with the ip and new port 8892 go to : http://localhost:8891/#/
 
  ## Analyze
  
  Now you can use Zepelin to load all csv with our code and you have to create the table corresponding to your need and configure databases and push your data after preprocessing.
  
  *Enjoy !*