pipeline {
    agent {
        docker {
            image 'jenkins-python'
        }
    }
    stages {
        stage('Resolve dependencies') {
            steps {
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
