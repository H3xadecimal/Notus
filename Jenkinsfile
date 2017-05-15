pipeline {
    agent any
    stages {
        stage('Resolve dependencies') {
            steps {
                sh 'git clone https://github.com/Rapptz/discord.py --branch rewrite'
                sh 'mv discord.py/discord discord'
            }
        }
        stage('Test') {
            steps {
                sh 'cloc --exclude-dir=discord .'
                sh 'flake8 --exclude=discord --show-source --max-line-length 120 .'
                sh 'python3 -m compileall -x discord .'
            }
        }
    }
    post {
        always {
            deleteDir()
        }
    }
}
