pipeline {
    agent {
        docker {
            image 'ubuntu'
        }
    }
    stages {
        stage('Resolve dependencies') {
            steps {
                sh 'apt update'
                sh 'apt upgrade -y'
                sh 'apt install python3 python3-dev python3-pip libffi-dev cloc -y'
                sh 'pip3 install flake8'
                sh 'pip3 install git+https://github.com/Rapptz/discord.py@rewrite'
            }
        }
        stage('Test') {
            steps {
                sh 'cloc .'
                sh 'flake8 --show-source --max-line-length 120 .'
                sh 'python3 -m compileall .'
            }
        }
    }
    post {
        always {
            deleteDir()
        }
    }
}
