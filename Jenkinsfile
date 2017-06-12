pipeline {
    agent {
        docker {
            image 'ubuntu'
            args '-u 0'
        }
    }
    stages {
        stage('Resolve dependencies') {
            steps {
                sh 'whoami'
                sh 'apt-get update'
                sh 'apt-get upgrade -y'
                sh 'apt-get install python3 python3-dev python3-pip libffi-dev cloc git -y'
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
