from flask import Flask, make_response, request, jsonify
from datetime import datetime, timezone, timedelta, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, ForeignKey, Column, Date, Boolean, Cast, func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
from flask_marshmallow import Marshmallow
import os
import uuid
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from flask_jwt_extended import get_jwt_identity, get_jwt
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from passlib.hash import sha256_crypt
from sqlalchemy import text
from flask_cors import CORS, cross_origin
from flask_caching import Cache
# Init app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:rcsew8676@127.0.0.1/mydb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "super-secret"
jwt = JWTManager(app)

app.config['JWT_COOKIE_SECURE'] = True
app.config['JWT_COOKIE_SAMESITE'] = 'None'
config = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}
app.config.from_mapping(config)
cache = Cache(app)

ma = Marshmallow()

url = 'mysql://root:rcsew8676@127.0.0.1/mydb'
engine = create_engine(url, echo=True)
connection = engine.connect()
cors = CORS(app, resources={r"/*": {"origins": "http://localhost:3000", "methods": ["GET", "POST", "PUT", "DELETE"], "supports_credentials": True}})


def mydefault():
     idnum = uuid.uuid1()
     return str(idnum)

# declarative base class
class Base(DeclarativeBase):
    pass

# an example mapping using the base
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=mydefault())
    username = Column(String(50), unique=True)
    password = Column(String(50))

Session = sessionmaker(bind=engine)
session = Session()


class Employee(Base):
    __tablename__ = "employees"
    employeeID = Column(String(36), primary_key=True)
    firstName = Column(String(50))
    lastName = Column(String(50))
    DOB = Column(Date)
    email = Column(String(50))
    skillLevelID = Column(String(36), ForeignKey("skilllevels.skillLevelID"))
    active = Column(Boolean)
    
class EmployeeSchema(ma.Schema):
    class Meta:
        fields = ('employeeID', 'firstName', 'lastName', 'DOB', 'email', 'skillLevelID','active', 'skillName', 'description')

        
employee_schema = EmployeeSchema()
employees_schema = EmployeeSchema(many=True)

class SkillLevel(Base):
    __tablename__ = "skilllevels"

    skillLevelID = Column(String(36), primary_key=True)
    skillName = Column(String(50))
    description = Column(String(250))
    
class SkillLevelSchema(ma.Schema):
    class Meta:
        fields = ('skillName', 'description')
skillLevels_schema = SkillLevelSchema(many=True)


@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        return response



@app.route('/employee', methods=['POST'])
@cross_origin(origin='http://localhost:3000', supports_credentials=True)
@jwt_required(locations=["cookies"])
def add_employee():
    new_employee = Employee()
    new_employee.employeeID = str(uuid.uuid1())
    new_employee.firstName = request.json['firstName']
    new_employee.lastName = request.json['lastName']
    new_employee.DOB = request.json['DOB']
    new_employee.email = request.json['email']
    new_employee.active = request.json['active']
    skillName = request.json['skillName']
    resp = session.query(SkillLevel).filter(SkillLevel.skillName == skillName)
    if(resp.count() == 0):
        return "Invalid Skill Level", 400
    
    new_employee.skillLevelID = resp.first().skillLevelID
    if(datetime.strptime(new_employee.DOB, '%Y-%m-%d') > datetime.today()):
        return "Invalid Date", 400
    session.rollback()
    session.add(new_employee)
    session.commit()
    return new_employee.employeeID, 201

@app.route('/employee', methods=['GET'])
@cross_origin(origin='http://localhost:3000', supports_credentials=True)
@jwt_required(locations=["cookies"])
def get_employees():
    all_employees = session.query(Employee.employeeID, Employee.firstName, Employee.lastName, Employee.DOB, Employee.email, Employee.skillLevelID, Employee.active, SkillLevel.skillName, SkillLevel.description).join(SkillLevel, Employee.skillLevelID == SkillLevel.skillLevelID).all()
    result = employees_schema.dump(all_employees)
    response = make_response(jsonify(result))
    for i in result:
        print(i)
    return response

@app.route('/skilllevels', methods=['GET'])
@cross_origin(origin='http://localhost:3000', supports_credentials=True)
@jwt_required(locations=["cookies"])
@cache.cached(timeout=3600)
def get_skillLevels():
    session.rollback()
    skillLevels = session.query(SkillLevel).all()
    result = skillLevels_schema.dump(skillLevels)
    response = make_response(jsonify(result))
    return response

@app.route('/authenticate', methods=['POST'])
@cross_origin(origin='http://localhost:3000', supports_credentials=True)
def authenticate_user():
    auth = request.authorization
    if not auth or not auth.username or not auth.password: 
        return make_response('could not verify', 401, {'Authentication': 'login required"'})
    user = session.query(User).filter(User.username == auth.username.lower())
    if(user.count() < 1):
        return make_response('Invalid username or password. Please try again.', 401)
    if(not sha256_crypt.verify(auth.password, user.first().password)):
        return make_response('Invalid username or password. Please try again.', 401)
    access_token = create_access_token(identity=user.first().username)
    resp = make_response(jsonify(access_token))
    set_access_cookies(resp, access_token)
    return resp



@app.route('/employee/<id>', methods=['PUT'])
@cross_origin(origin='http://localhost:3000', supports_credentials=True)
@jwt_required(locations=["cookies"])
def edit_employee(id):
    if(datetime.strptime(request.json["DOB"], '%Y-%m-%d') > datetime.today()):
        return "Invalid Date", 400
    session.rollback()
    employee = session.query(Employee).filter(Employee.employeeID == id)
    if(employee.count==0):
        return "Invalid Employee", 400
    employee.first().firstName = request.json['firstName']
    employee.first().lastName = request.json['lastName']
    employee.first().DOB = request.json['DOB']
    employee.first().email = request.json['email']
    employee.first().active = request.json['active']
    skillName = request.json['skillName']
    employee.first().skillLevelID = session.query(SkillLevel).filter(SkillLevel.skillName == skillName).first().skillLevelID
    session.commit()
    return employee_schema.jsonify(employee.first())

@app.route('/employee/<id>', methods=['DELETE'])
@cross_origin(origin='http://localhost:3000', supports_credentials=True)
@jwt_required(locations=["cookies"])
def delete_employee(id):
    session.rollback()
    employee = session.query(Employee).filter(Employee.employeeID == id)
    session.delete(employee.first())
    session.commit()
    return "Employee Successfully Deleted"

@app.route('/logout', methods=['POST'])
@cross_origin(origin='http://localhost:3000', supports_credentials=True)
def remove_cookies():
    resp = jsonify({'logout': True})
    unset_jwt_cookies(resp)
    return resp, 200

# Run Server
if __name__ == '__main__':
     app.run(debug=True)
