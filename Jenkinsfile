pipeline {
    agent {
        docker {
            image 'chinodesuuu/ci-amethyst'
        }
    }
    stages {
        stage('Test') {
            steps {
                sh 'cloc --exclude-dir=discord --exclude-dir=discord.py .'
                sh 'flake8 --exclude=discord,discord.py --show-source --max-line-length 120 .'
                sh '/usr/bin/python3.6 -m compileall -x discord.* .'
            }
        }
    }
    post {
        always {
            sh 'rm -rf * | true'
        }
    }
}
